# Configuração do Launchd

## Execução automática, todo dia as 18:30 para Mac OS:

### Etapa 1:
No terminal, acesse a pasta Library/LaunchAgents

### Etapa 2:
Crie o arquivo launchd:
```
nano ~/Library/LaunchAgents/com.seunome.coleta.precos.plist
```
OBS: substituia "seunome" acima por um apelido, suas iniciais ou seu nome mesmo.

### Etapa 3: Código do arquivo .plist

#### 3.1: Edite o "CAMINHO_DA_SUA_PASTA"
Cole o código abaixo dentro do arquivo e substitua todos os "CAMINHO_DA_SUA_PASTA" abaixo pelo caminho correto no seu computador.

#### 3.2: Edite o "seunome"
Substitua o "seunome" do código conforme etapa 2.

#### Nota 1: 
Eu uso o anaconda, caso não use altera a linha com "<string>/opt/anaconda3/bin/python3</string>".

#### Nota 2:
Caso o script não rode, verifique se o Python possui permissão de execução e se o macOS não bloqueou o processo por segurança (System Settings → Privacy & Security).

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">

<plist version="1.0">
<dict>

    <key>Label</key>
    <string>com.seunome.coleta.precos</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/anaconda3/bin/python3</string>
        <string>/Users/CAMINHO_DA_SUA_PASTA/scripts/coleta_precos.py</string>
    </array>

    <!-- Diretório correto para paths relativos -->
    <key>WorkingDirectory</key>
    <string>/Users/CAMINHO_DA_SUA_PASTA/scripts</string>

    <!-- Executa todos os dias às 18:30 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <!-- Permite rodar imediatamente ao carregar -->
    <key>RunAtLoad</key>
    <true/>

    <!-- Logs -->
    <key>StandardOutPath</key>
    <string>/Users/CAMINHO_DA_SUA_PASTA/logs/launchd.out</string>

    <key>StandardErrorPath</key>
    <string>/Users/CAMINHO_DA_SUA_PASTA/logs/launchd.err</string>

</dict>
</plist>
```
### Etapa 4:
Salve as alterações e feche o arquivo:
```
control + O > salvar
Enter
control + X > sair
````

### Etapa 5:
Para carregar o arquivo, abra o terminal e execute o código abaixo:

```
launchctl load ~/Library/LaunchAgents/com.seunome.coleta.precos.plist
```

### Etapa 6:
Force a execução manual:

```
launchctl kickstart -k gui/$(id -u)/com.seunome.coleta.precos
````

### Etapa 7:
Para validar que funcionou:

```
tail -n 50 ~/CAMINHO_DA_SUA_PASTA/logs/launchd.err
tail -n 50 ~/CAMINHO_DA_SUA_PASTA/logs/launchd.out
tail -n 50 ~/CAMINHO_DA_SUA_PASTA/logs/coleta.log
````

Será exibido algo como:

```
==== Início da coleta de preços ====
Processando FLRY3.SA
...
==== Fim da coleta de preços ====
````

### Etapa 8 - OPCIONAL: Editando o launchd

Caso precise editar o arquivo .plist (launchd):

```
nano ~/Library/LaunchAgents/com.seunome.coleta.precos.plist
````

#### Faça as alterações que deseja.

```
control + O > salvar
Enter
control + X > sair
````

Após editar, descarreue e carregue o arquivo editado:

```
launchctl unload ~/Library/LaunchAgents/com.seunome.coleta.precos.plist
launchctl load ~/Library/LaunchAgents/com.seunome.coleta.precos.plist
````

Force a execução manual:
```
launchctl kickstart -k gui/$(id -u)/com.seunome.coleta.precos
```

<h2>Author:</h2> 

Douglas Senra


