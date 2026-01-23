# SPDX-License-Identifier: AGPL-3.0-only
#
# Copyright (c) 2026 Pacta Contributors
#
# This file is part of Pacta.
#
# Pacta is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Pacta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.

from dataclasses import dataclass

from pacta.core.config import EngineConfig
from pacta.ir.merge import DefaultIRMerger
from pacta.ir.normalize import DefaultIRNormalizer
from pacta.ir.types import ArchitectureIR
from pacta.mapping.enricher import DefaultArchitectureEnricher
from pacta.model.loader import DefaultArchitectureModelLoader
from pacta.model.resolver import DefaultModelResolver
from pacta.model.types import ArchitectureModel
from pacta.model.validator import DefaultArchitectureModelValidator
from pacta.plugins.interfaces import AnalyzeConfig
from pacta.plugins.registry import AnalyzerRegistry
from pacta.reporting.builder import DefaultReportBuilder
from pacta.reporting.keys import DefaultViolationKeyFactory
from pacta.reporting.types import EngineError, Report, RunInfo, Violation
from pacta.rules.compiler import RulesCompiler
from pacta.rules.dsl import DefaultDSLParser
from pacta.rules.evaluator import DefaultRuleEvaluator
from pacta.rules.loader import DefaultRuleSourceLoader
from pacta.rules.types import RuleSet
from pacta.snapshot.baseline import DefaultBaselineService
from pacta.snapshot.builder import DefaultSnapshotBuilder
from pacta.snapshot.diff import DefaultSnapshotDiffEngine
from pacta.snapshot.store import FsSnapshotStore
from pacta.snapshot.types import Snapshot, SnapshotDiff
from pacta.vcs.git import GitVCSProvider


@dataclass(frozen=True)
class ScanResult:
    snapshot: Snapshot
    report: Report
    diff: SnapshotDiff | None


# Default engine wiring


class DefaultPactaEngine:
    """
    The orchestrator. It wires components and runs the full pipeline.
    """

    def __init__(self) -> None:
        # Plugins/analyzers
        self.registry = AnalyzerRegistry()

        # IR pipeline
        self.ir_merger = DefaultIRMerger()
        self.ir_normalizer = DefaultIRNormalizer()

        # Model
        self.model_loader = DefaultArchitectureModelLoader()
        self.model_validator = DefaultArchitectureModelValidator()
        self.model_resolver = DefaultModelResolver()

        # Mapping/enrichment
        self.enricher = DefaultArchitectureEnricher()

        # Rules
        self.rule_source_loader = DefaultRuleSourceLoader()
        self.dsl_parser = DefaultDSLParser()
        self.rule_compiler = RulesCompiler()
        self.rule_evaluator = DefaultRuleEvaluator()

        # Snapshot/diff/baseline
        self.snapshot_builder = DefaultSnapshotBuilder()
        # Note: snapshot_store is created per-scan with repo_root
        self.diff_engine = DefaultSnapshotDiffEngine()
        self.key_factory = DefaultViolationKeyFactory()
        self.baseline_service = DefaultBaselineService()

        # Reporting
        self.report_builder = DefaultReportBuilder()

        # VCS (optional)
        self.vcs = GitVCSProvider()

    def scan(self, cfg: EngineConfig) -> ScanResult:
        engine_errors: list[EngineError] = []
        violations: tuple[Violation] = tuple()
        diff: SnapshotDiff | None = None

        # Create snapshot store for this scan
        snapshot_store = FsSnapshotStore(repo_root=str(cfg.repo_root))

        # ----------------------------
        # 0) VCS context (optional)
        # ----------------------------
        commit = self.vcs.current_commit(cfg.repo_root)

        # ----------------------------
        # 1) Load analyzers
        # ----------------------------
        self.registry.load_entrypoints()
        selected = self.registry.best_for_repo(cfg.repo_root)
        if not selected:
            engine_errors.append(
                EngineError(
                    type="config_error",
                    message="No analyzers found for this repository",
                    location=None,
                    details={"hint": "Install an analyzer plugin (e.g., pacta-python) or ensure source files exist."},
                )
            )
            # Continue: still produce a report with engine errors.

        # ----------------------------
        # 2) Analyze (produce raw IRs)
        # ----------------------------
        from pacta.plugins.interfaces.analyzer import AnalyzeTarget

        analyze_cfg = AnalyzeConfig(
            repo_root=cfg.repo_root,
            target=AnalyzeTarget(
                include_paths=cfg.include_paths,
                exclude_globs=cfg.exclude_globs,
            ),
            deterministic=cfg.deterministic,
            language_options={},
        )

        raw_irs: list[ArchitectureIR] = []
        for loaded in selected:
            try:
                raw_irs.append(loaded.analyzer.analyze(analyze_cfg))
            except Exception as e:
                engine_errors.append(
                    EngineError(
                        type="runtime_error",
                        message=f"Analyzer '{loaded.analyzer.plugin_id}' failed",
                        location=None,
                        details={"error": repr(e), "analyzer": loaded.analyzer.plugin_id},
                    )
                )

        # ----------------------------
        # 3) Merge + normalize IR
        # ----------------------------
        combined_ir = self.ir_merger.merge(raw_irs) if raw_irs else ArchitectureIR.empty(cfg.repo_root)
        normalized_ir = self.ir_normalizer.normalize(combined_ir)

        # ----------------------------
        # 4) Load + validate model (architecture.yaml)
        # ----------------------------
        model: ArchitectureModel | None = None
        if cfg.model_file and cfg.model_file.exists():
            try:
                model = self.model_loader.load(cfg.model_file)
                engine_errors.extend(self.model_validator.validate(model))
                model = self.model_resolver.resolve(model)
            except Exception as e:
                engine_errors.append(
                    EngineError.from_dict(
                        {
                            "type": "config_error",
                            "message": "Failed to load architecture model",
                            "location": {"file": str(cfg.model_file), "start": {"line": 1, "column": 1}},
                            "details": {"error": repr(e)},
                        }
                    )
                )
                model = None

        # ----------------------------
        # 5) Enrich IR using model mapping
        # ----------------------------
        enriched_ir = normalized_ir
        if model is not None:
            try:
                enriched_ir = self.enricher.enrich(normalized_ir, model)
            except Exception as e:
                engine_errors.append(
                    EngineError(
                        type="runtime_error",
                        message="Failed to enrich IR with architecture model mapping",
                        location=None,
                        details={"error": repr(e)},
                    )
                )

        # ----------------------------
        # 6) Load + parse + compile rules
        # ----------------------------
        try:
            sources = self.rule_source_loader.load_sources(cfg.rules_files)
            ast_file = self.dsl_parser.parse_many(sources, source_names=[str(p) for p in cfg.rules_files])
            ruleset: RuleSet = self.rule_compiler.compile(ast_file)
        except Exception as e:
            engine_errors.append(
                EngineError(
                    type="rules_error",
                    message="Failed to load/parse/compile rules",
                    location=None,
                    details={"error": repr(e)},
                )
            )
            ruleset = RuleSet()

        # ----------------------------
        # 7) Evaluate rules -> violations
        # ----------------------------
        try:
            violations = self.rule_evaluator.evaluate(enriched_ir, ruleset)
        except Exception as e:
            engine_errors.append(
                EngineError(
                    type="runtime_error",
                    message="Rule evaluation failed",
                    location=None,
                    details={"error": repr(e)},
                )
            )
            violations = tuple()

        # ----------------------------
        # 8) Build snapshot and load baseline snapshot (optional)
        # ----------------------------
        from pacta.snapshot.types import SnapshotMeta

        # Build snapshot with violations included (for baseline comparison)
        snapshot = self.snapshot_builder.build(
            enriched_ir,
            meta=SnapshotMeta(
                repo_root=str(cfg.repo_root),
                commit=commit,
            ),
            violations=violations,
        )

        baseline_snapshot: Snapshot | None = None
        if cfg.baseline:
            if snapshot_store.exists(cfg.baseline):
                baseline_snapshot = snapshot_store.load(cfg.baseline)
                diff = self.diff_engine.diff(baseline_snapshot, snapshot)
                violations = self.baseline_service.mark_status(
                    violations=violations,
                    baseline_snapshot=baseline_snapshot,
                    key_factory=self.key_factory,
                )
            else:
                engine_errors.append(
                    EngineError(
                        type="config_error",
                        message=f"Baseline snapshot not found: {cfg.baseline}",
                        location=None,
                        details={"hint": "Create a baseline with `pacta scan --save-ref <name>`"},
                    )
                )

        # Save snapshot under save_ref if specified, otherwise default to "latest"
        ref = cfg.save_ref if cfg.save_ref else "latest"
        snapshot_store.save(snapshot, ref=ref)

        # ----------------------------
        # 9) Build report
        # ----------------------------
        report = self.report_builder.build(
            run=RunInfo(
                repo_root=str(cfg.repo_root),
                commit=commit,
                model_file=str(cfg.model_file) if cfg.model_file else None,
                rules_files=tuple(str(p) for p in cfg.rules_files),
                baseline_ref=cfg.baseline,
                mode="changed_only" if cfg.changed_only else "full",
            ),
            violations=violations,
            engine_errors=engine_errors,
            diff=diff,
        )

        return ScanResult(snapshot=snapshot, report=report, diff=diff)

    def build_ir(self, cfg: EngineConfig) -> ArchitectureIR:
        """
        Build the architecture IR without running rules.

        This runs only the analysis and enrichment pipeline:
          1. Load analyzers
          2. Analyze (produce raw IRs)
          3. Merge + normalize IR
          4. Load + validate model (optional)
          5. Enrich IR using model mapping (optional)

        Use this for `snapshot save` when you want to capture architecture
        structure without evaluating rules.

        Args:
            cfg: Engine configuration (repo_root and optionally model_file)

        Returns:
            The enriched ArchitectureIR

        Raises:
            RuntimeError: If no analyzers are found or analysis fails
        """
        from pacta.plugins.interfaces.analyzer import AnalyzeTarget

        # ----------------------------
        # 1) Load analyzers
        # ----------------------------
        self.registry.load_entrypoints()
        selected = self.registry.best_for_repo(cfg.repo_root)
        if not selected:
            raise RuntimeError(
                "No analyzers found for this repository. "
                "Install an analyzer plugin (e.g., pacta-python) or ensure source files exist."
            )

        # ----------------------------
        # 2) Analyze (produce raw IRs)
        # ----------------------------
        analyze_cfg = AnalyzeConfig(
            repo_root=cfg.repo_root,
            target=AnalyzeTarget(
                include_paths=cfg.include_paths,
                exclude_globs=cfg.exclude_globs,
            ),
            deterministic=cfg.deterministic,
            language_options={},
        )

        raw_irs: list[ArchitectureIR] = []
        errors: list[str] = []
        for loaded in selected:
            try:
                raw_irs.append(loaded.analyzer.analyze(analyze_cfg))
            except Exception as e:
                errors.append(f"Analyzer '{loaded.analyzer.plugin_id}' failed: {e!r}")

        if not raw_irs:
            raise RuntimeError(f"All analyzers failed: {'; '.join(errors)}")

        # ----------------------------
        # 3) Merge + normalize IR
        # ----------------------------
        combined_ir = self.ir_merger.merge(raw_irs)
        normalized_ir = self.ir_normalizer.normalize(combined_ir)

        # ----------------------------
        # 4) Load + validate model (optional)
        # ----------------------------
        model: ArchitectureModel | None = None
        if cfg.model_file and cfg.model_file.exists():
            model = self.model_loader.load(cfg.model_file)
            validation_errors = self.model_validator.validate(model)
            if validation_errors:
                # Log warnings but continue
                for err in validation_errors:
                    print(f"Model validation warning: {err.message}")
            model = self.model_resolver.resolve(model)

        # ----------------------------
        # 5) Enrich IR using model mapping
        # ----------------------------
        enriched_ir = normalized_ir
        if model is not None:
            enriched_ir = self.enricher.enrich(normalized_ir, model)

        return enriched_ir
