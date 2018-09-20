# If your LogRhythm Agent runs as a user other than NT AUTHORITY\SYSTEM, put that in the variable below:
# EG MYDOMAIN\LogRhythm
$agent_user = 'BUCKLEHQ\justine'

#Requires -RunAsAdministrator

$path       = 'C:\LogRhythm\logrhythm-duo'
$executable = "python $path\logrhythm-duo.py"
$taskName   = 'Download Duo logs for LogRhythm'

$action   = New-ScheduledTaskAction -execute $executable
$trigger  = New-ScheduledTaskTrigger -At (Get-Date).Date -Once -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

try {
  Register-ScheduledTask -ErrorAction Stop -TaskName $taskName -Trigger $trigger -Action $action -Setting $settings -User "NT AUTHORITY\SYSTEM" -RunLevel 1
} catch {
  Write-Host "Scheduled task already exists, skipping."
}
Set-ScheduledTask $taskName -Trigger $trigger

# Configure script directory
if (!(Test-Path ($path))) {
  New-Item -Path $path -ItemType directory
}
# Copy things over to the new location
$robocopy_args = "/e"
if (Test-Path ("$path\duo.conf")) {
  $robocopy_args += " /xf duo.conf"
}
$source = (Get-Item $PSScriptRoot).parent.Fullname
robocopy $source $path $robocopy_args


$acl = get-acl $path
# Disable and delete inheritance
$acl.SetAccessRuleProtection($true,$false)

# SYSTEM can read and execute
$AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule('NT AUTHORITY\SYSTEM', "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($AccessRule)

# Admins can read and modify
$AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule('BUILTIN\Administrators', "Read,Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($AccessRule)

# LogRhythm agent gets read
if ($agent_user) {
  $AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($agent_user, "ReadAndExecute", "None", "None", "Allow")
  $acl.SetAccessRule($AccessRule)
}

$acl | Set-Acl $path


# Configure logs directory
$acl = get-acl "$path\logs"

#SYSTEM can write logs
$AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule('NT AUTHORITY\SYSTEM', "Read,Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($AccessRule)

#LogRhythm agent can write logs
if ($agent_user) {
  $AccessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($agent_user, "Read,Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
  $acl.SetAccessRule($AccessRule)
}

$acl | Set-Acl "$path\logs"