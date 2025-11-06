#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven

import os
import time
import logging
import requests
from pyVmomi import vim
from aria.ops.event import Criticality

logger = logging.getLogger(__name__)

prefix = "VCFOperationsvCommunity-"
suffix = "-Services-TEMP"
current_directory = os.path.dirname(os.path.abspath(__file__))
serviceLogScript = "getWindowsServices.ps1"
serviceScriptPath = os.path.join(current_directory, "getWindowsServices.ps1")


def fileTransfer(vm, creds, content, scriptPath, tempDir, script):
    try:
        with open(scriptPath, "rb") as f:
            data = f.read()

        remotePath = f"{tempDir}\\{script}"
        fileManager = content.guestOperationsManager.fileManager
        fileAttr = vim.vm.guest.FileManager.FileAttributes()

        url = fileManager.InitiateFileTransferToGuest(
            vm=vm,
            auth=creds,
            guestFilePath=remotePath,
            fileAttributes=fileAttr,
            fileSize=len(data),
            overwrite=True
        )

        response = requests.put(url, data=data, verify=False)
        if response.status_code == 200:
            logger.info(f"Successfully transferred the {remotePath} file to {vm.name}")
            return True
        else:
            logger.error(f"File transfer failed to {vm.name}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.exception(f"Exception during file transfer to {vm.name}: {e}")
        return False


def executeProgram(powershellPath, command, processManager, vm, creds):
    programSpec = vim.vm.guest.ProcessManager.ProgramSpec(
        programPath=powershellPath,
        arguments=f"-Command \"{command}\""
    )
    pid = processManager.StartProgram(vm, creds, programSpec)
    if pid <= 0:
        raise logger.error(f"Command execution failed on {vm.name}")
    else:   
        logger.info(f"Powershell command has been executed by command: {command} , PID: {pid}")
        while True:
            processInfo = processManager.ListProcessesInGuest(vm, creds, [pid]).pop()
            if processInfo.exitCode is not None:
                logger.info(f"Code execution finished, exit code: {processInfo.exitCode}")
                break


def checkFile(fileManager, vm, creds, tempDir, fileName):
    try:
        fileInfo = fileManager.ListFilesInGuest(
            vm=vm,
            auth=creds,
            filePath=tempDir,
            index=0,
            maxResults=100
        )

        if fileInfo.files:
            for file in fileInfo.files:
                if file.path.lower() == fileName.lower():
                    logger.info(f"{fileName} file found in {tempDir} on {vm.name}")
                    return True
        return False
   
    except vim.fault.FileNotFound:
        logger.info(f"Couldn't find the {fileName} in {vm.name}")
        return False
    except Exception as e:
        logger.error(f"There was an error during file check. {e}")
        return False


def readOutput(fileManager, vm, creds, filePath):
    readFile = fileManager.InitiateFileTransferFromGuest(vm, creds, filePath)
    response = requests.request("GET", readFile.url, headers={}, data={}, verify=False)
    if response.status_code == 200:
        logger.info(f"Successfuly downloaded the file: {filePath} from {vm.name}")
        return response.text
    else:
        logger.error(f"Can not download powershell output from {vm.name}. Expected file is: {filePath}")


def createTempFile(fileManager, vm, creds, filePath, data):
    try:
        tempFile = fileManager.CreateTemporaryFileInGuest(vm, creds, prefix="events", suffix=".xml", directoryPath=filePath)
        fileAttr = vim.vm.guest.FileManager.FileAttributes()
        url = fileManager.InitiateFileTransferToGuest(
            vm=vm,
            auth=creds,
            guestFilePath=tempFile,
            fileAttributes=fileAttr,
            fileSize=len(data),
            overwrite=True
        )

        response = requests.put(url, data=data, verify=False)
        if response.status_code == 200:
            logger.info(f"XML data successfully written to {tempFile} on {vm.name}")
            return True, tempFile
        else:
            logger.error(f"Failed to write file. HTTP status: {response.status_code} on {vm.name}")
            return False, None
    except Exception as e:
        logger.error(f"Exception during file creation on {vm.name}: {e}")
        return False, None

def collect_vm_service_properties(vm_obj, vm, content, winUser, winPassword, winServiceConfigFile):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)

    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus == "toolsOk" and guestOSFamily == "windowsGuest":
        logger.info(f"Started Windows Service monitoring for {vm.name}")
        systemRootPath = "C:\\Windows"
        tempDirPath = systemRootPath + "\\Temp"
        powershellPath = systemRootPath + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        try:
            tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, tempDirPath)

            serviceList = "@(" + ", ".join([f"'{s}'" for s in winServiceConfigFile]) + ")"
            command = f"\"& '{tempDir}\\{serviceLogScript}' @({serviceList}) | Export-Csv -Path '{tempDir}\\Services.csv' -NoTypeInformation -Encoding UTF8\""
            fileTransferStatus = fileTransfer(vm, creds, content, serviceScriptPath, tempDir, serviceLogScript)
            if fileTransferStatus:
                executeProgram(powershellPath, command, processManager, vm, creds)
                servicesOutputPath = f"{tempDir}\\Services.csv"
                serviceResult = readOutput(fileManager, vm, creds, servicesOutputPath)
                logger.error(f"serviceResult: {serviceResult}")
                lines = serviceResult.splitlines()
                logger.error(f"lines: {lines}")
                if serviceResult.strip():
                    logger.error(f"serviceResult.strip(): {serviceResult.strip()}")
                    header = lines[0].split(',')
                    serviceNameIndex = header.index('"Name"')
                    serviceDisplayNameIndex = header.index('"DisplayName"')
                    serviceStatusIndex = header.index('"Status"')
                    serviceStartTypeIndex = header.index('"StartType"')
                    for line in lines[1:]:
                        columns = line.split(',')
                        serviceName = columns[serviceNameIndex].strip('"')
                        serviceDisplayName = columns[serviceDisplayNameIndex].strip('"')
                        serviceStatus = columns[serviceStatusIndex].strip('"')
                        serviceStartType = columns[serviceStartTypeIndex].strip('"')
                        vm_obj.with_property(f"vCommunity|Guest OS|Services|{serviceDisplayName}|Service Name", serviceName)
                        vm_obj.with_property(f"vCommunity|Guest OS|Services|{serviceDisplayName}|Service Status", serviceStatus)
                        vm_obj.with_property(f"vCommunity|Guest OS|Services|{serviceDisplayName}|Service Start Type", serviceStartType)

                        logger.info(f"Sending Windows Event details for {vm.name}")
                else:
                    logger.info(f"Can not find Windows Event details on {vm.name}")
            else:
                logger.error(f"Cannot find the Windows Event Log XML file on {vm.name}")

            if tempDir and fileTransferStatus:
                try:
                    fileManager.DeleteDirectory(vm, creds, tempDir, True)
                    logger.info(f"Temp folder {tempDir} has been cleared on {vm.name}")
                except Exception as e:
                    logger.error(f"Failed to delete temp folder {tempDir} on {vm.name}: {e}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory on {vm.name}: {e}")
            return
    else:
        logger.info(f"Skipping {vm.name} is not a Windows Guest.")