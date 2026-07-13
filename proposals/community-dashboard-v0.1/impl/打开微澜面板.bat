@echo off
rem WeiLan community dashboard one-click launcher (keep ASCII: cmd codepage safe)
set LAUNCHER=D:\WeilanSkillEvolution\proposals\community-dashboard-v0.1\impl\launch_dashboard.py
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%LAUNCHER%"
) else (
  start "" /min python "%LAUNCHER%"
)
