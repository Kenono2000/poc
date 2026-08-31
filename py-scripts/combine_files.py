import os

parts = {
    "combined_part_1_core_and_labs.txt": [
        "suntiq-product/README.md",
        "suntiq-product/AGENTS.md",
        "suntiq-product/CLAUDE.md",
        "suntiq-product/docs/onboarding/README.md",
        "suntiq-product/docs/onboarding/ARCHITECTURE.md",
        "suntiq-product/docs/onboarding/TRANSITION.md",
        "suntiq-product/docs/onboarding/BACKLOG.md",
        "suntiq-product/docs/fleet/ENVIRONMENTS.md",
        "suntiq-product/docs/Homepage Breakdown.md",
        "suntiq-product/apps/www/docs/SEO_AEO_CHECKLIST.md",
        "suntiq-product/apps/www/docs/PRD.md",
        "suntiq-product/apps/www/docs/OUTBOUND_SALES_PRD.md",
        "suntiq-product/packages/ui-web/AGENTS.md",
        "suntiq-product/packages/ui-web/CLAUDE.md",
        "suntiq-product/packages/ui-tokens/AGENTS.md",
        "suntiq-product/packages/ui-tokens/CLAUDE.md",
        "suntiq-product/packages/ui-native/AGENTS.md",
        "suntiq-product/packages/ui-native/CLAUDE.md",
        "suntiq-product/labs/README.md",
        "suntiq-product/labs/ml/FINDINGS.md",
        "suntiq-product/labs/ml/argo-ml-research-repo/README.md",
        "suntiq-product/labs/ml/argo-ml-deliverable/argo-ml/README.md"
    ],
    "combined_part_2_apps.txt": [
        "suntiq-product/apps/fleet-dashboard/README.md",
        "suntiq-product/apps/fleet-dashboard/AGENTS.md",
        "suntiq-product/apps/fleet-dashboard/CLAUDE.md",
        "suntiq-product/apps/fleet-dashboard/convex/README.md",
        "suntiq-product/apps/fleet-mobile/README.md",
        "suntiq-product/apps/fleet-mobile/AGENTS.md",
        "suntiq-product/apps/fleet-mobile/CLAUDE.md",
        "suntiq-product/apps/consumer-mobile/README.md",
        "suntiq-product/apps/consumer-mobile/AGENTS.md",
        "suntiq-product/apps/consumer-mobile/CLAUDE.md",
        "suntiq-product/apps/www/README.md",
        "suntiq-product/apps/www/AGENTS.md",
        "suntiq-product/apps/www/CLAUDE.md",
        "suntiq-product/apps/ui-docs/README.md",
        "suntiq-product/apps/ui-docs/AGENTS.md",
        "suntiq-product/apps/ui-docs/CLAUDE.md"
    ],
    "combined_part_3_research_gtm.txt": [
        "suntiq-product/docs/research/suntiq-gtm-2026-08/README.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/gtm-operating-system.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/foundation-pack.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/final-direction.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/content-refresh-brief.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/gtm-validation-activation-kit.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ASSET_INDEX.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/tribunal/report.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/user-and-agent-research.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/summary.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/study-design.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/source-map.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/constraint-bundle.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/persona-detection.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/regional-operations-leader.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/peak-season-member.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/owner-finance-lead.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/integration-gatekeeper.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/fleet-maintenance-lead.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/dock-turnaround-manager.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/assumptions-falsifiers.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/competitor-marketing-sales.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/implicit-truths.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/consensus-blindspots-white-space.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/investor-attack.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/prelaunch-product-study-plan.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/pilot-experiment-plan.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/external-validator.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/conversation-guide.md"
    ]
}

for output_file, input_files in parts.items():
    with open(output_file, "w", encoding="utf-8") as outfile:
        for file_path in input_files:
            outfile.write(f"\n{'='*80}\n")
            outfile.write(f"FILE: {file_path}\n")
            outfile.write(f"{'='*80}\n\n")
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as infile:
                        outfile.write(infile.read())
                else:
                    outfile.write(f"ERROR: File not found at {file_path}\n")
            except OSError as e:
                outfile.write(f"ERROR: Could not read file {file_path}: {e!s}\n")
            outfile.write("\n")
    print(f"Created {output_file}")
