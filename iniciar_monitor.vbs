' Loud Voice Cooldown - Iniciar sem terminal visível
' Este script inicia a aplicação em background usando pythonw (sem janela de console).
'
' INSTRUÇÃO: Edite a linha abaixo com o caminho real onde você clonou o projeto.
' Exemplo: "C:\Users\Rodrigo\Documents\loud-voice-cooldown"

Dim caminhoProjeto
caminhoProjeto = Replace(WScript.ScriptFullName, "\" & WScript.ScriptName, "")

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = caminhoProjeto
WshShell.Run "cmd /c """ & caminhoProjeto & "\venv\Scripts\pythonw.exe"" """ & caminhoProjeto & "\main.py""", 0, False
