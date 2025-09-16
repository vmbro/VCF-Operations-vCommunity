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
suffix = "-EventLog-TEMP"
current_directory = os.path.dirname(os.path.abspath(__file__))
eventLogScript = "getWindowsEventLogs.ps1"
eventLogScriptPath = os.path.join(current_directory, "getWindowsEventLogs.ps1")


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

def collect_windows_events(vm_obj, vm, content, winUser, winPassword, winEventLogConfigFile):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)

    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus == "toolsOk" and guestOSFamily == "windowsGuest":
        logger.info(f"Started Windows Event log reading for {vm.name}")
        systemRootPath = "C:\\Windows"
        tempDirPath = systemRootPath + "\\Temp"
        powershellPath = systemRootPath + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        try:
            tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, tempDirPath)
            tempFileStatus, tempFile = createTempFile(fileManager, vm, creds, tempDir, winEventLogConfigFile)
            tempFileName = tempFile.split("EventLog-TEMP\\")[-1]
            FileExist = checkFile(fileManager, vm, creds, tempDir, tempFileName)

            if tempFileStatus and FileExist:
                command = f"\"& '{tempDir}\\{eventLogScript}' '{tempFile}' | Export-Csv -Path '{tempDir}\\Event_Log.csv' -NoTypeInformation -Encoding UTF8\""
                fileTransferStatus = fileTransfer(vm, creds, content, eventLogScriptPath, tempDir, eventLogScript)
                if fileTransferStatus:
                    executeProgram(powershellPath, command, processManager, vm, creds)
                    eventLogOutputPath = f"{tempDir}\\Event_Log.csv"
                    eventLogResult = readOutput(fileManager, vm, creds, eventLogOutputPath)
                    lines = eventLogResult.splitlines()
                    if eventLogResult.strip():
                        header = lines[0].split(',')
                        eventLevelIndex = header.index('"Level"')
                        eventMessageIndex = header.index('"Event"')
                        for line in lines[1:]:
                            columns = line.split(',')
                            eventLevel = columns[eventLevelIndex].strip('"')
                            eventMessage = columns[eventMessageIndex].strip('"')

                            if eventLevel == "Information":
                                criticality = Criticality.INFO
                            elif eventLevel == "Verbose":
                                criticality = Criticality.INFO
                            elif eventLevel == "Warning":
                                criticality = Criticality.WARNING
                            elif eventLevel == "Error":
                                criticality = Criticality.IMMEDIATE
                            elif eventLevel == "Critical":
                                criticality = Criticality.CRITICAL
                            else:
                                criticality = Criticality.INFO

                            formattedMessage = f"[WindowsEvent-{eventLevel} {eventMessage}"
                            #vm_obj.with_event(message = formattedMessage, criticality=criticality)
                            now = int(time.time() * 1000)
                            vm_obj.with_event(
                                message=formattedMessage,
                                criticality=criticality,
                                auto_cancel=True,
                                watch_wait_cycle=1,
                                cancel_wait_cycle=3,
                                update_date=now
                            )
                            logger.info(f"Sending Windows Event details for {vm.name}")
                    else:
                        logger.info(f"Can not find Windows Event details on {vm.name}")
                else:
                    logger.info(f"File transfer failed. Skipping Windows Event Log reading on {vm.name} ")
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