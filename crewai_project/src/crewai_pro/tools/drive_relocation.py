"""Drive relocation analyzer tool.

Analyses the source drive for large relocatable folders/files and emits a
human-readable summary plus JSON + CSV reports on disk.

SAFETY: This tool NEVER moves or deletes files. It only reports.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from crewai.tools import BaseTool


class DriveRelocationAnalyzerTool(BaseTool):
    name: str = "Drive Relocation Analyzer"
    description: str = (
        "Analyzes the source drive for large relocatable items and compares with "
        "other drives. NEVER moves or deletes files automatically."
    )

    RELOCATABLE_FOLDERS: ClassVar[list[str]] = [
        r"{user_profile}\Documents",
        r"{user_profile}\Downloads",
        r"{user_profile}\Pictures",
        r"{user_profile}\Videos",
        r"{user_profile}\Music",
        r"{user_profile}\Desktop",
        r"{user_profile}\AppData\Local\Steam",
        r"{user_profile}\AppData\Local\EpicGames",
        r"{user_profile}\AppData\Local\Battle.net",
        r"{user_profile}\AppData\Local\Riot Games",
        r"{user_profile}\AppData\Local\Docker",
        r"{user_profile}\AppData\Local\Programs",
        r"{user_profile}\.conda",
        r"{user_profile}\.virtualenvs",
        r"{user_profile}\.cache",
        r"{user_profile}\.nuget",
        r"{user_profile}\.gradle",
        r"{user_profile}\.m2",
        r"{user_profile}\scoop",
        r"{user_profile}\AppData\Local\Google\Chrome\User Data",
        r"{user_profile}\AppData\Local\Microsoft\Edge\User Data",
        r"{user_profile}\AppData\Roaming\Spotify\Storage",
        r"{user_profile}\AppData\Local\Discord",
    ]

    FORBIDDEN_FOLDERS: ClassVar[list[str]] = [
        r"C:\Windows",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\ProgramData\Microsoft",
        r"C:\Users\Default",
        r"C:\Recovery",
    ]

    def _run(
        self,
        source_drive: str = "C:",
        target_drive: str = "D:",
        min_folder_size_mb: int = 500,
    ) -> str:
        user_profile = os.environ.get("USERPROFILE", r"C:\Users\Default")
        username = os.path.basename(user_profile)

        analysis: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "source_drive": source_drive,
            "target_drive": target_drive,
            "username": username,
            "user_profile": user_profile,
            "source_drive_info": self._get_drive_info(source_drive),
            "target_drive_info": self._get_drive_info(target_drive),
            "relocatable_folders": [],
            "large_files": [],
            "recommendations": [],
        }

        for folder_template in self.RELOCATABLE_FOLDERS:
            folder_path = Path(folder_template.format(user_profile=user_profile))
            if not folder_path.exists():
                continue
            try:
                folder_size = self._get_folder_size(folder_path)
                folder_size_mb = folder_size / (1024 * 1024)
                if folder_size_mb < min_folder_size_mb:
                    continue
                analysis["relocatable_folders"].append(
                    {
                        "path": str(folder_path),
                        "size_mb": round(folder_size_mb, 2),
                        "size_gb": round(folder_size_mb / 1024, 2),
                        "file_count": self._count_files(folder_path),
                        "relocatable": True,
                        "relocation_method": self._get_relocation_method(folder_path),
                        "risk_level": self._assess_risk(folder_path),
                    }
                )
            except (PermissionError, OSError):
                continue

        analysis["large_files"] = self._find_large_files(
            Path(f"{source_drive}\\"),
            min_size_mb=100,
            max_files=50,
        )
        analysis["recommendations"] = self._generate_recommendations(analysis)
        self._save_reports(analysis)
        return self._format_summary(analysis)

    def _get_drive_info(self, drive_letter: str) -> dict[str, Any]:
        try:
            total, used, free = shutil.disk_usage(f"{drive_letter}\\")
            return {
                "drive": drive_letter,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 1),
            }
        except Exception as exc:
            return {"drive": drive_letter, "error": str(exc)}

    def _get_folder_size(self, path: Path) -> int:
        total = 0
        try:
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue
                try:
                    total += file_path.stat().st_size
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        return total

    def _count_files(self, path: Path) -> int:
        count = 0
        try:
            for _ in path.rglob("*"):
                count += 1
        except (PermissionError, OSError):
            pass
        return count

    def _get_relocation_method(self, path: Path) -> str:
        path_str = str(path).lower()
        if any(
            folder in path_str
            for folder in ["documents", "downloads", "pictures", "videos", "music", "desktop"]
        ):
            return "Windows Location Tab (Right-click folder → Properties → Location)"
        if "steam" in path_str:
            return "Steam Settings → Storage → Move Install Folder"
        if "epicgames" in path_str:
            return "Epic Games Launcher → Move Install"
        if "docker" in path_str:
            return "Docker Desktop → Settings → Resources → Advanced → Disk image location"
        dev_tools = [".conda", ".virtualenvs", ".cache", ".nuget", ".gradle", ".m2", "scoop"]
        if any(tool in path_str for tool in dev_tools):
            return "Manual move + Create symbolic link (mklink /D)"
        return "Manual move + Update app settings"

    def _assess_risk(self, path: Path) -> str:
        path_str = str(path).lower()
        if any(x in path_str for x in ["downloads", "pictures", "videos", "music"]):
            return "LOW - Safe to relocate"
        if any(x in path_str for x in [".cache", ".conda", ".virtualenvs", "docker"]):
            return "MEDIUM - May require reconfiguration"
        if "user data" in path_str or "appdata" in path_str:
            return "MEDIUM-HIGH - Apps may need path updates"
        return "MEDIUM - Review before relocating"

    def _find_large_files(
        self, drive_path: Path, min_size_mb: int = 100, max_files: int = 50
    ) -> list[dict[str, Any]]:
        large_files: list[dict[str, Any]] = []
        try:
            for file_path in drive_path.rglob("*"):
                if not file_path.is_file():
                    continue
                try:
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    if size_mb >= min_size_mb:
                        large_files.append(
                            {
                                "path": str(file_path),
                                "size_mb": round(size_mb, 2),
                                "size_gb": round(size_mb / 1024, 2),
                            }
                        )
                except (PermissionError, OSError):
                    continue
                if len(large_files) >= max_files:
                    break
        except (PermissionError, OSError):
            pass
        return sorted(large_files, key=lambda x: x["size_mb"], reverse=True)

    def _generate_recommendations(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        sorted_folders = sorted(
            analysis["relocatable_folders"], key=lambda x: x["size_mb"], reverse=True
        )
        recommendations = []
        for folder in sorted_folders[:10]:
            recommendations.append(
                {
                    "priority": "HIGH" if folder["size_gb"] > 5 else "MEDIUM",
                    "folder": folder["path"],
                    "size_gb": folder["size_gb"],
                    "method": folder["relocation_method"],
                    "risk": folder["risk_level"],
                    "estimated_savings_mb": folder["size_mb"],
                }
            )
        return recommendations

    def _save_reports(self, analysis: dict[str, Any]) -> None:
        with open("drive_relocation_analysis.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        with open("relocation_recommendations.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Priority",
                    "Folder_Path",
                    "Size_GB",
                    "Relocation_Method",
                    "Risk_Level",
                    "Estimated_Savings_MB",
                ]
            )
            for rec in analysis["recommendations"]:
                writer.writerow(
                    [
                        rec["priority"],
                        rec["folder"],
                        rec["size_gb"],
                        rec["method"],
                        rec["risk"],
                        rec["estimated_savings_mb"],
                    ]
                )

    def _format_summary(self, analysis: dict[str, Any]) -> str:
        line = "=" * 80
        summary = f"{line}\n📊 DRIVE RELOCATION ANALYSIS REPORT\n{line}\n\n"
        summary += f"🔍 Analysis Date: {analysis['timestamp']}\n"
        summary += f"👤 User: {analysis['username']}\n\n"

        summary += "💾 DRIVE STATUS:\n"
        src = analysis["source_drive_info"]
        if "error" not in src:
            summary += (
                f"   Source ({analysis['source_drive']}): "
                f"{src['used_gb']}GB used / {src['total_gb']}GB total "
                f"({src['percent_used']}% full)\n"
            )
        else:
            summary += f"   Error: {src['error']}\n"

        tgt = analysis["target_drive_info"]
        if "error" not in tgt:
            summary += (
                f"   Target ({analysis['target_drive']}): "
                f"{tgt['free_gb']}GB free / {tgt['total_gb']}GB total\n"
            )
        else:
            summary += f"   Error: {tgt['error']}\n"

        total_relocatable_gb = sum(f["size_gb"] for f in analysis["relocatable_folders"])
        summary += "\n📦 RELOCATION OPPORTUNITIES:\n"
        summary += f"   Relocatable folders found: {len(analysis['relocatable_folders'])}\n"
        summary += f"   Total potential savings: {total_relocatable_gb:.2f} GB\n"
        summary += f"   Large files (>100MB): {len(analysis['large_files'])}\n"

        summary += "\n🎯 TOP RECOMMENDATIONS:\n"
        for i, rec in enumerate(analysis["recommendations"][:5], 1):
            summary += f"\n   {i}. {rec['folder']}\n"
            summary += f"      Size: {rec['size_gb']:.2f} GB | Priority: {rec['priority']}\n"
            summary += f"      Method: {rec['method']}\n"
            summary += f"      Risk: {rec['risk']}\n"

        summary += (
            f"\n{line}\n"
            "📋 Detailed reports saved:\n"
            "   - drive_relocation_analysis.json (full data)\n"
            "   - relocation_recommendations.csv (spreadsheet view)\n"
            "\n⚠️  IMPORTANT: Review all recommendations before relocating anything!\n"
            f"{line}\n"
        )
        return summary