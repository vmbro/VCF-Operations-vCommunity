#  Copyright 2025 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import os
import logging
import requests
import csv
from io import StringIO
from pyVmomi import vim

logger = logging.getLogger(__name__)

prefix = "VCFOperationsvCommunity-"
suffix = "-OSInfo-TEMP"
current_directory = os.path.dirname(os.path.abspath(__file__))
osInfoScript = "getWindowsOSInformation.ps1"
osInfoScriptPath = os.path.join(current_directory, "getWindowsOSInformation.ps1")


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

def collect_vm_os_information_properties(vm_obj, vm, content, winUser, winPassword):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)

    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus == "toolsOk" and guestOSFamily == "windowsGuest":
        logger.info(f"Collecting Windows OS Information properties for {vm.name}")
        systemRootPath = "C:\\Windows"
        tempDirPath = systemRootPath + "\\Temp"
        powershellPath = systemRootPath + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        try:
            tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, tempDirPath)

            command = f"\"& '{tempDir}\\{osInfoScript}' | Export-Csv -Path '{tempDir}\\OSInfo.csv' -NoTypeInformation -Encoding UTF8\""
            fileTransferStatus = fileTransfer(vm, creds, content, osInfoScriptPath, tempDir, osInfoScript)
            if fileTransferStatus:
                executeProgram(powershellPath, command, processManager, vm, creds)
                OSInfoOutputPath = f"{tempDir}\\OSInfo.csv"
                OSInfoResult = readOutput(fileManager, vm, creds, OSInfoOutputPath)
                reader = csv.reader(StringIO(OSInfoResult))
                rows = list(reader)
                if rows:
                    header = rows[0]
                    osNameIndex = header.index("Name")
                    osVersionIndex = header.index("Version")
                    osBuildNumberIndex = header.index("BuildNumber")
                    osOSArchitectureIndex = header.index("OSArchitecture")
                    osLastBootUpTimeIndex = header.index("LastBootUpTime")
                    osReleaseIdIndex = header.index("ReleaseId")

                    for row in rows[1:]:
                        try:
                            osName = row[osNameIndex]
                            osVersion = row[osVersionIndex]
                            osBuildNumber = row[osBuildNumberIndex]
                            osOSArchitecture = row[osOSArchitectureIndex]
                            osLastBootUpTime = row[osLastBootUpTimeIndex]
                            osReleaseId = row[osReleaseIdIndex]
                            logger.info(f"Parsed OS Information for {vm.name}: Name={osName}, Version={osVersion}, BuildNumber={osBuildNumber}, Architecture={osOSArchitecture}, LastBootUpTime={osLastBootUpTime}, ReleaseId={osReleaseId}")
                        except Exception as e:
                            logger.error(f"CSV parsing error on {vm.name}: {e}")
                            continue

                        vm_obj.with_property(f"vCommunity|Guest OS|Operating System|OS Name", osName)
                        vm_obj.with_property(f"vCommunity|Guest OS|Operating System|OS Version", osVersion)
                        vm_obj.with_property(f"vCommunity|Guest OS|Operating System|OS BuildNumber", osBuildNumber)
                        vm_obj.with_property(f"vCommunity|Guest OS|Operating System|OS Architecture", osOSArchitecture)
                        vm_obj.with_property(f"vCommunity|Guest OS|Operating System|OS Last Boot Up Time", osLastBootUpTime)
                        vm_obj.with_property(f"vCommunity|Guest OS|Operating System|OS Release ID", osReleaseId)

                        logger.info(f"Sending Windows Operating System informations for {vm.name}")
                else:
                    logger.info(f"Can not find Windows Operating System informations on {vm.name}")
            else:
                logger.error(f"Cannot find the Windows Operating System information CSV file on {vm.name}")

        except Exception as e:
            logger.error(f"Failed to create temporary directory on {vm.name}: {e}")
            return
        
        finally:
            try:
                if tempDir:
                    fileManager.DeleteDirectoryInGuest(vm, creds, tempDir, True)
            except:
                pass
    else:
        logger.info(f"Skipping {vm.name} is not a Windows Guest.")