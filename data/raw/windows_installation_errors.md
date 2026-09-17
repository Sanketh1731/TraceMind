# Windows Software Installation & Package Manager Troubleshooting Guide

## Overview
This runbook covers critical installation, package extraction, and deployment failures encountered by software developers and system administrators on Windows 10, Windows 11, and Windows Server environments.

---

## 1. Error Code 0x80070005 – Access Denied (E_ACCESSDENIED)

### Problem Description
The installation or package extraction terminates abruptly with the error:
`Error: 0x80070005 Access Denied while installing package`
or `HRESULT: 0x80070005 - General access denied error`.

### Root Cause Analysis
Error `0x80070005` indicates that the current user process lacks the required Windows Discretionary Access Control List (DACL) write privileges to the destination directory or target registry hive. 
The primary causes are:
1. The process was launched from a standard non-elevated user token attempting to write to protected system directories such as `%ProgramFiles%`, `%ProgramData%`, or `C:\Windows\System32`.
2. Antivirus or Windows Defender Controlled Folder Access (CFA) is actively blocking untrusted binaries from writing to user profiles or program directories.
3. Leftover file locks by previous crashed installation instances or background services holding exclusive read/write handles on target binaries.

### Grounded Actionable Fix Steps
1. **Elevate Command Prompt / PowerShell as Administrator**:
   Right-click PowerShell or Windows Terminal and select **Run as Administrator**, or re-execute the installer using elevated privileges:
   ```powershell
   Start-Process msiexec.exe -ArgumentList '/i "package.msi" /qn /L*v "install.log"' -Verb runAs
   ```
2. **Grant Full Control DACL to Target Installation Directory**:
   If installing to custom directories (e.g. `C:\Tools\` or `C:\ProgramData\App`), reset permissions using `icacls`:
   ```cmd
   takeown /F "C:\ProgramData\App" /R /A /D Y
   icacls "C:\ProgramData\App" /grant Administrators:F /T /C
   ```
3. **Check Controlled Folder Access**:
   Navigate to **Windows Security > Virus & threat protection > Ransomware protection > Controlled folder access**. If enabled, click **Allow an app through Controlled folder access** and whitelist the installer binary.
4. **Terminate Conflicting Background File Handles**:
   Identify processes locking the destination directory using `handle.exe` or PowerShell:
   ```powershell
   Get-Process -Name "*installer*", "*msiexec*" | Stop-Process -Force
   ```

---

## 2. Error Code 0x80070002 – ERROR_FILE_NOT_FOUND

### Problem Description
During setup or dependency resolution, the system reports:
`Error: 0x80070002 The system cannot find the file specified.`

### Root Cause Analysis
The installer manifest references an external payload or cab archive that is missing from the working directory, corrupted during download, or quarantined by real-time malware analysis.

### Grounded Actionable Fix Steps
1. **Clear Temp Cache and Validate Checksums**:
   Delete cached artifacts in `%TEMP%` and `%LOCALAPPDATA%\Temp`, then re-download with sha256 checksum verification:
   ```powershell
   Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
   ```
2. **Repair Windows Component Store**:
   Run System File Checker and DISM:
   ```cmd
   DISM.exe /Online /Cleanup-image /Restorehealth
   sfc /scannow
   ```

---

## 3. Error Code 1603 – Fatal Error During Installation

### Problem Description
`MSI (s): MainEngineThread is returning 1603. Fatal error during installation.`

### Root Cause Analysis
Error 1603 is a generic MSI catch-all error thrown when:
1. The target installation folder is encrypted via EFS (Encrypting File System).
2. The `SYSTEM` account lacks full permissions to the installation destination.
3. A custom action DLL inside the MSI package exited with a non-zero return code.

### Grounded Actionable Fix Steps
1. Ensure the SYSTEM account has Full Control on the target directory:
   ```cmd
   icacls "C:\Program Files\TargetApp" /grant SYSTEM:(OI)(CI)F
   ```
2. Inspect the verbose MSI log for the first `Return value 3` line to identify the exact failing CustomAction.
