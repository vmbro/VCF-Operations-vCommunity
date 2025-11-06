param (
    [Parameter(Mandatory = $true)]
    [string[]]$serviceList
)

$output = @()

foreach ($service in $serviceList) {
    try {
        $svc = Get-Service -Name $service -ErrorAction SilentlyContinue |
            Select-Object Name, DisplayName, Status, StartType
        if ($svc) {
            $output += $svc
        } else {
            Write-Host "Service not found: $service"
        }
    }
    catch {
        Write-Host "Error retrieving service: $service"
    }
}

return $output