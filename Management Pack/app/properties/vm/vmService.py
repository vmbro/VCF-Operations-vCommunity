#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import requests
from pyVmomi import vim

logger = logging.getLogger(__name__)

prefix = "vSphereContentMP-"
suffix = "-will-be-deleted"

def collect_vm_service_properties(vm_obj, vm, content, winUser, winPassword):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)
    command = '''Get-Service | Where-Object { $_.StartType -match \\"Automatic\\" } | Select-Object DisplayName, Status, StartType | Sort-Object DisplayName'''
    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus == "toolsOk" and guestOSFamily == "windowsGuest":
        logger.info(f"Started service monitoring for {vm}")
        systemRootPath = "C:\\Windows"
        logger.info(f"Collecting service informations from {vm}")
        tempDirPath = systemRootPath + "\\Temp"
        powershellPath = systemRootPath + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        logger.info(f"Collecting service informations from {vm}")
        tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, tempDirPath)
        exportCSV = ''' | Export-Csv -Path "{}\\services.csv" -NoTypeInformation'''.format(tempDir)
        command += exportCSV

        programSpec = vim.vm.guest.ProcessManager.ProgramSpec(
            programPath=powershellPath,
            arguments=f"-Command \"{command}\""
        )

        pid = processManager.StartProgram(vm, creds, programSpec)

        if pid <= 0:
            raise logger.error(f"Command execution failed on {vm}")
        logger.info(f"Command executed, PID: {pid}")

        while True:
            processInfo = processManager.ListProcessesInGuest(vm, creds, [pid]).pop()
            if processInfo.exitCode is not None:
                print(f"Code execution finished, exit code: {processInfo.exitCode}")
                break

        servicesFilePath = tempDir + "\\services.csv"
        readFile = fileManager.InitiateFileTransferFromGuest(vm, creds, servicesFilePath)
        response = requests.request("GET", readFile.url, headers={}, data={}, verify=False)
        if response.status_code == 200:
            logger.info(f"Successfuly downloaded services list from {vm}")
            services = response.text
            deleteTempDir = fileManager.DeleteDirectory(vm, creds, tempDir, True)
            lines = services.splitlines()
            header = lines[0].split(',')
            serviceNameIndex = header.index('"DisplayName"')
            serviceStatusIndex = header.index('"Status"')
            serviceStartTypeIndex = header.index('"StartType"')
            for line in lines[1:]:
                columns = line.split(',')
                serviceName = columns[serviceNameIndex].strip('"')
                serviceStatus = columns[serviceStatusIndex].strip('"')
                serviceStartType = columns[serviceStartTypeIndex].strip('"')
                vm_obj.with_property(f"Summary|Guest|Services|{serviceName}|Service Name", serviceName)
                vm_obj.with_property(f"Summary|Guest|Services|{serviceName}|Service Status", serviceStatus)
                vm_obj.with_property(f"Summary|Guest|Services|{serviceName}|Service Start Type", serviceStartType)
        else:
            logger.error(f"Can not download powershell output from {vm}")
    else:
        logger.debug(f"{vm} is not a WindowsGuest.")