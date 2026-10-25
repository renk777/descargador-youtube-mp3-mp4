Option Explicit

Dim shell, scriptDir, pythonw, command
Set shell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonw = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python312\pythonw.exe"

If Not CreateObject("Scripting.FileSystemObject").FileExists(pythonw) Then
    pythonw = "pythonw.exe"
End If

command = """" & pythonw & """ """ & scriptDir & "\descargador.py"""
shell.Run command, 0, False
