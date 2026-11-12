Option Explicit
Dim shell, files, scriptDir, executable, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
scriptDir = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir
executable = scriptDir & "\dist\Descargador.exe"
If files.FileExists(executable) Then
    command = """" & executable & """"
Else
    command = "pythonw.exe """ & scriptDir & "\descargador.py"""
End If
On Error Resume Next
shell.Run command, 0, False
If Err.Number <> 0 Then
    MsgBox "No se pudo iniciar Descargador. Compila el proyecto o instala Python y requirements.txt.", vbExclamation, "Descargador"
End If
