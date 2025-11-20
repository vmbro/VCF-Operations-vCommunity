$output = @()

$os = Get-CimInstance Win32_OperatingSystem
$reg = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"

$output += [PSCustomObject]@{
    Name           = $os.Caption
    Version        = $os.Version
    BuildNumber    = $os.BuildNumber
    OSArchitecture = $os.OSArchitecture
    LastBootUpTime = $os.LastBootUpTime
    ReleaseId      = $reg.ReleaseId
}

return $output