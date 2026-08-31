import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, ClassVar
from crewai.tools import BaseTool

class DriveRelocationAnalyzerTool(BaseTool):
    name: str = "Drive Relocation Analyzer"
    description: str = "Analyzes C: drive for large relocatable items and compares with other drives. NEVER moves or deletes files automatically."
    
    # Folders that are SAFE to relocate (user data, media, games, dev tools)
    RELOCATABLE_FOLDERS: ClassVar[List[str]] = [
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
    
    # NEVER relocate these (system-critical)
    FORBIDDEN_FOLDERS: ClassVar[List[str]] = [
        r"C:\Windows",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\ProgramData\Microsoft",
        r"C:\Users\Default",
        r"C:\Recovery",
    ]
    
    def _run(self, source_drive: str = "C:", target_drive: str = "D:", min_folder_size_mb: int = 500) -> str:
        """Analyze drives for relocation opportunities."""
        
        user_profile = os.environ.get('USERPROFILE', r'C:\Users\Default')
        username = os.path.basename(user_profile)
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "source_drive": source_drive,
            "target_drive": target_drive,
            "username": username,
            "user_profile": user_profile,
            "source_drive_info": self._get_drive_info(source_drive),
            "target_drive_info": self._get_drive_info(target_drive),
            "relocatable_folders": [],
            "large_files": [],
            "recommendations": []
        }
        
        # Analyze relocatable folders
        for folder_template in self.RELOCATABLE_FOLDERS:
            folder_path = folder_template.format(user_profile=user_profile)
            path = Path(folder_path)
            
            if not path.exists():
                continue
            
            try:
                folder_size = self._get_folder_size(path)
                folder_size_mb = folder_size / (1024 * 1024)
                
                if folder_size_mb >= min_folder_size_mb:
                    folder_info = {
                        "path": str(path),
                        "size_mb": round(folder_size_mb, 2),
                        "size_gb": round(folder_size_mb / 1024, 2),
                        "file_count": self._count_files(path),
                        "relocatable": True,
                        "relocation_method": self._get_relocation_method(path),
                        "risk_level": self._assess_risk(path)
                    }
                    analysis["relocatable_folders"].append(folder_info)
            except (PermissionError, OSError):
                continue
        
        # Find large files on source drive
        analysis["large_files"] = self._find_large_files(
            Path(f"{source_drive}\\"),
            min_size_mb=100,
            max_files=50
        )
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        # Save detailed report
        self._save_reports(analysis)
        
        return self._format_summary(analysis)
    
    def _get_drive_info(self, drive_letter: str) -> Dict[str, Any]:
        """Get drive space information."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(f"{drive_letter}\\")
            return {
                "drive": drive_letter,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 1)
            }
        except Exception as e:
            return {"drive": drive_letter, "error": str(e)}
    
    def _get_folder_size(self, path: Path) -> int:
        """Calculate total folder size in bytes."""
        total = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    try:
                        total += file_path.stat().st_size
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        return total
    
    def _count_files(self, path: Path) -> int:
        """Count files in folder."""
        count = 0
        try:
            for _ in path.rglob("*"):
                count += 1
        except (PermissionError, OSError):
            pass
        return count
    
    def _get_relocation_method(self, path: Path) -> str:
        """Determine the best method to relocate this folder."""
        path_str = str(path).lower()
        
        if any(folder in path_str for folder in ["documents", "downloads", "pictures", "videos", "music", "desktop"]):
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
        """Assess risk level of relocating this folder."""
        path_str = str(path).lower()
        
        if any(x in path_str for x in ["downloads", "pictures", "videos", "music"]):
            return "LOW - Safe to relocate"
        if any(x in path_str for x in [".cache", ".conda", ".virtualenvs", "docker"]):
            return "MEDIUM - May require reconfiguration"
        if "user data" in path_str or "appdata" in path_str:
            return "MEDIUM-HIGH - Apps may need path updates"
        
        return "MEDIUM - Review before relocating"
    
    def _find_large_files(self, drive_path: Path, min_size_mb: int = 100, max_files: int = 50) -> List[Dict]:
        """Find large files on the drive."""
        large_files = []
        
        try:
            for file_path in drive_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                try:
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    
                    if size_mb >= min_size_mb:
                        large_files.append({
                            "path": str(file_path),
                            "size_mb": round(size_mb, 2),
                            "size_gb": round(size_mb / 1024, 2)
                        })
                except (PermissionError, OSError):
                    continue
                
                if len(large_files) >= max_files:
                    break
        except (PermissionError, OSError):
            pass
        
        return sorted(large_files, key=lambda x: x["size_mb"], reverse=True)
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate prioritized relocation recommendations."""
        recommendations = []
        
        sorted_folders = sorted(
            analysis["relocatable_folders"],
            key=lambda x: x["size_mb"],
            reverse=True
        )
        
        for folder in sorted_folders[:10]:
            recommendations.append({
                "priority": "HIGH" if folder["size_gb"] > 5 else "MEDIUM",
                "folder": folder["path"],
                "size_gb": folder["size_gb"],
                "method": folder["relocation_method"],
                "risk": folder["risk_level"],
                "estimated_savings_mb": folder["size_mb"]
            })
        
        return recommendations
    
    def _save_reports(self, analysis: Dict):
        """Save detailed reports to files."""
        with open("drive_relocation_analysis.json", 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        with open("relocation_recommendations.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Priority", "Folder_Path", "Size_GB", "Relocation_Method", 
                "Risk_Level", "Estimated_Savings_MB"
            ])
            
            for rec in analysis["recommendations"]:
                writer.writerow([
                    rec["priority"],
                    rec["folder"],
                    rec["size_gb"],
                    rec["method"],
                    rec["risk"],
                    rec["estimated_savings_mb"]
                ])
    
    def _format_summary(self, analysis: Dict) -> str:
        """Format analysis summary."""
        summary = "=" * 80 + "\n"
        summary += "📊 DRIVE RELOCATION ANALYSIS REPORT\n"
        summary += "=" * 80 + "\n\n"
        
        summary += f"🔍 Analysis Date: {analysis['timestamp']}\n"
        summary += f"👤 User: {analysis['username']}\n\n"
        
        summary += "💾 DRIVE STATUS:\n"
        summary += f"   Source ({analysis['source_drive']}): "
        src = analysis['source_drive_info']
        if 'error' not in src:
            summary += f"{src['used_gb']}GB used / {src['total_gb']}GB total ({src['percent_used']}% full)\n"
        else:
            summary += f"Error: {src['error']}\n"
        
        summary += f"   Target ({analysis['target_drive']}): "
        tgt = analysis['target_drive_info']
        if 'error' not in tgt:
            summary += f"{tgt['free_gb']}GB free / {tgt['total_gb']}GB total\n"
        else:
            summary += f"Error: {tgt['error']}\n"
        
        total_relocatable_gb = sum(f["size_gb"] for f in analysis["relocatable_folders"])
        summary += f"\n📦 RELOCATION OPPORTUNITIES:\n"
        summary += f"   Relocatable folders found: {len(analysis['relocatable_folders'])}\n"
        summary += f"   Total potential savings: {total_relocatable_gb:.2f} GB\n"
        summary += f"   Large files (>100MB): {len(analysis['large_files'])}\n"
        
        summary += f"\n🎯 TOP RECOMMENDATIONS:\n"
        for i, rec in enumerate(analysis["recommendations"][:5], 1):
            summary += f"\n   {i}. {rec['folder']}\n"
            summary += f"      Size: {rec['size_gb']:.2f} GB | Priority: {rec['priority']}\n"
            summary += f"      Method: {rec['method']}\n"
            summary += f"      Risk: {rec['risk']}\n"
        
        summary += "\n" + "=" * 80 + "\n"
        summary += "📋 Detailed reports saved:\n"
        summary += "   - drive_relocation_analysis.json (full data)\n"
        summary += "   - relocation_recommendations.csv (spreadsheet view)\n"
        summary += "\n⚠️  IMPORTANT: Review all recommendations before relocating anything!\n"
        summary += "=" * 80 + "\n"
        
        return summary
