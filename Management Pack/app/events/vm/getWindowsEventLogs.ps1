param (
    [Parameter(Mandatory = $true)]
    [string]$XmlPath
)

$output = @()
$MinutesToCheck = 5
[xml]$config = Get-Content $XmlPath

$startTime = (Get-Date).AddMinutes(-$MinutesToCheck)
$now = Get-Date

foreach ($log in $config.Events.Log) {
    $logName = $log.Name
    $eventIDs = $log.EventID
    
    if (-not [string]::IsNullOrEmpty($eventIDs)) {
        Write-Host "Starting to collect event details : $startTime → $now Checking logs for $logName (EventIDs: $($eventIDs -join ', '))" -ForegroundColor Cyan

        foreach ($eventID in $eventIDs) {
            try {
                $events = Get-WinEvent -FilterHashtable @{
                    LogName   = $logName
                    Id        = $eventID
                    StartTime = $startTime
                } -ErrorAction SilentlyContinue
            }
            catch {
                Write-Host "Failed to read event details (Log=$logName, EventID=$eventID)"
                continue
            }

            $eventCount = $events.Count

            if ($eventCount -gt 0) {
                $firstEvent = $events[0]

                $level = $($firstEvent.LevelDisplayName)

                $eventDetails = "[Timestamp=$($firstEvent.TimeCreated)] [Category=$($firstEvent.LogName)] [EventID=$eventID] [Source=$($firstEvent.ProviderName)] [Message=$($firstEvent.Message)]"
                Write-Host $eventDetails -ForegroundColor Red

                $output += [PSCustomObject]@{
                    Level = $level
                    Event = $eventDetails
                }
            }
        }
    }

}

return $output