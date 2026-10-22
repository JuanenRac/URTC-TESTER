<p align="center">
  <img src="/images/URTC_TESTER_BANNER.svg" alt="Logótipo do URTC Tester" width="100%">
</p>

# URTC Tester (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  🇵🇹 <b>Português</b>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>


**Versão:** 0.3.9 · **Autor:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Licença: **GPL-3.0-or-later** para o código-fonte, **CC BY-SA 4.0** para esta
documentação - consulte `LICENSE` neste repositório, ou a secção "License and
Copyright Notices" no final deste documento.

Um exercitador de barramento CAN em tempo real para a placa URTC. Liga-se através do mesmo
adaptador USB-CAN que o flasher utiliza, pergunta à placa para qual dos seus 25 perfis de
ferramenta está atualmente configurada com jumpers e mostra apenas os controlos e a telemetria
dessa ferramenta - não uma janela a tentar representar as 25 ao mesmo tempo. Tudo o que faz é
um comando em tempo de execução ou uma leitura de telemetria sobre a aplicação atualmente em
execução; nunca toca na flash, pelo que nada aqui pode deixar a placa menos funcional do que
estava ao início.

**Verificação de honestidade - o que realmente funciona hoje:** os codificadores de payload CAN para as famílias de controlo Qt Quick migradas (`advanced_protocol.py`) são reais e estão cobertos pelos testes de `tests/` (`python -m pytest -q`). O CI deste repositório (`.github/workflows/ci.yml`) também os executa, juntamente com `ruff check`, `tools/ci_validate.py`, uma compilação de sintaxe de cada ficheiro `.py` e os quatro scripts `verify_qt_*.py`, pelo que uma regressão aí faz falhar a compilação. Os quatro scripts `verify_qt_*.py` na raiz do repositório (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) são verificações end-to-end reais, deliberadamente fora de `tests/`, contra um transporte simulado com entrega real de Signals entre threads - os quatro passam com `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, que o CI também executa. Esse é o limite honesto do que é verificado automaticamente: a camada de transporte, o tratamento dos IDs CAN/disposição de bytes e a lógica da ponte Qt Quick são reais e exercitados com frames simuladas, não com hardware real - como as "Limitações conhecidas" abaixo já indicam, isto foi construído sem acesso a USB, pelo que nada aqui foi ainda verificado numa placa real. `qt_tester.py` e `assets/qml/TesterDeck.qml` são a implementação real e substancial (milhares de linhas no total), exercitada pelos testes com placas simuladas e pelos scripts de verificação, e nunca por uma placa real.

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado e ainda não existe nenhuma placa URTC montada. Os bootloaders verificam as imagens de firmware com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica (prevista); as imagens de aplicação publicadas estão assinadas com a chave pública de desenvolvimento (`signing_key_kind: dev`), pelo que qualquer pessoa pode produzir uma imagem que o bootloader aceita; nada foi transmitido a uma placa real. Leia a [base de segurança](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.3.8` |
| Maturidade | Funcional |
| Tecnologia | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Destino | O PC de quem o usa |
| Em hardware real | Só simulado: testado com emuladores, dublês de teste ou simuladores; não há registo de execução em hardware real para esta versão |

## 1. 🆚 Relação com o flasher

Esta ferramenta e o [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) partilham a mesma camada de transporte (as classes SLCAN e
SocketCAN são idênticas), uma vez que ambas precisam, no fundo, apenas de colocar
frames CAN dentro e fora do mesmo tipo de adaptador, mas desempenham
funções fundamentalmente diferentes:

| | Flasher | Tester |
|---|---|---|
| Toca na flash | Sim (é esse o objetivo) | Nunca |
| Comunica com | O bootloader, sobretudo | A aplicação em execução |
| Finalidade | Atualizar o firmware | Exercitar/verificar o hardware real de uma cabeça de ferramenta |

Se não tem a certeza de qual precisa: se a placa já está a executar
firmware e quer verificar se uma ferramenta realmente funciona (o aquecedor aquece,
o motor roda, o LED acende), precisa desta.

## 2. 📦 Instalar e executar

O mesmo padrão do flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

Ou crie um binário autónomo: `build_exe.bat` no Windows, `./build_exe.sh`
no Linux. Ambos limpam primeiro `build/`/`dist/` e incluem `assets/` (o
banner e o ícone) no executável - consulte
[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md) para o percurso de validação
`build-test.bat`/`build-test.sh`, que não altera a versão e sobre o qual estes scripts de empacotamento
se constroem, e o README do próprio flasher para o raciocínio mais completo por detrás
dos próprios scripts de empacotamento, uma vez que se aplica aqui de forma idêntica.

**Versionamento:** `TESTER_VERSION` (em `tester_config.py`, apresentada na
barra de título, na caixa Sobre, nos registos de sessão e nos pacotes de depuração) segue
`MAJOR.MINOR.PATCH`. Ambos os scripts de compilação a incrementam automaticamente imediatamente antes
de cada compilação real através de `bump_version.py`, ao estilo de "conta-quilómetros" em base 10: PATCH
+1, transitando para MINOR assim que PATCH passa de 9 (p. ex. `0.1.9` → `0.2.0`).
Executar a partir do código-fonte (`python urtc_tester.py`) nunca lhe toca - apenas uma
execução real de `build_exe.bat`/`build_exe.sh` o faz. MAJOR nunca é incrementada
automaticamente, apenas à mão. Consulte `CHANGELOG.md` para o histórico de versões.

### Visual command deck

O command deck **Qt Quick** é agora o predefinido real:
~~~
python urtc_tester.py
~~~
Utiliza os transportes SLCAN/SocketCAN e inicia em modo apenas de escuta,
pelo que não pode transmitir até armar deliberadamente as verificações ativas. Cada
um dos comandos próprios dos 25 perfis de ferramenta tem aqui cobertura real e confirmada
(movimento, furação, AOI, eletroíman, pulso de soldadura por pontos/ultrassónica, projeção
de pasta, flying probe, inspeção térmica, os 5 atuadores com watchdog-keepalive,
telemetria de vácuo/scan-probe), cada um controlado da mesma forma: uma
correspondência de identidade, um modo ativo explicitamente armado e uma confirmação do utilizador em
QML antes de qualquer transmissão. Nada disto foi ainda verificado numa placa real - consulte "Limitações conhecidas" abaixo.

O painel também mostra os **valores em direto** da ferramenta detetada (temperatura com gráfico deslizante e exportação CSV, RPM, fins de curso; só escutam, por isso funcionam no modo só de escuta e junto a uma saída em funcionamento), executa o **autoteste**, avisa no cabeçalho quando a **verificação de saúde do bus** (uma consulta da ferramenta ativa a cada 3 segundos enquanto mais nada usa o bus) vê um problema, e tem uma caixa **Acerca do URTC Tester** com o Readme, a Licença e a página do GitHub, junto a **Guardar registos...**.

O cabeçalho da janela Qt Quick tem um seletor de idioma; a escolha é guardada e aplica-se no próximo arranque. Também consulta e repõe a posição do alimentador de fio do ferro de soldar (estimativa em malha aberta; a reposição pede confirmação). A sonda de identidade mostra também o número de patch do firmware quando a placa o envia (firmware URTC 0.3.5 e posterior); o firmware mais antigo mostra apenas maior.menor.

O fluxo de diagnóstico CAN em direto existente utiliza agora uma superfície de command deck azul-marinho/ciano: cabeçalho de produto, cartão de ligação de alto contraste, separadores de ferramentas claros, registo de sessão escuro e canal de progresso visível. Esta alteração visual e de acessibilidade não modifica a monitorização passiva nem o encaminhamento de comandos, e nada disto foi experimentado numa placa real.

### Cabeçalho e ferramentas

- **Cabeçalho** - o estado da ligação, o aviso de saúde do bus, o seletor de idioma (a escolha é guardada e aplica-se no próximo arranque) e a versão.
- **Guardar registos...** e **EXPORTAR SESSÃO (REGISTO COM HASH)** - o registo do ecrã como texto simples, ou um zip com o registo, um manifesto que o identifica pelo seu SHA-256 e o diagnóstico do sistema (ver «Registos e pacotes de depuração» abaixo).
- **Acerca do URTC Tester** - versão e autor, com botões para **Readme** (no idioma da interface, quando existe tradução), **Licença** e a página **GitHub do URTC** do projeto.

### Estrutura de ficheiros

Esta ferramenta está organizada em módulos por responsabilidade, puramente para
legibilidade - não há diferença funcional entre tê-los como
ficheiros separados ou como um único ficheiro grande. Consulte a secção
"📂 Repository Structure" perto do final deste documento para
a descrição completa ficheiro a ficheiro.

**Idioma**: inglês por predefinição. Alterado com o seletor de idioma no cabeçalho da janela - altera a interface (rótulos, botões, caixas de diálogo e mensagens de registo) para qualquer um dos 8 idiomas disponíveis, guardado
imediatamente em `config.json` junto a esta ferramenta, aplicado no próximo
arranque. As traduções residem em ficheiros de texto simples em `language/`
(`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`, `chinese.lng`, `japanese.lng`, `portuguese.lng`) como simples pares `KEY=Value`,
um por linha - as linhas que começam
por `#` e as linhas em branco são ignoradas, e um `\n` literal dentro de um valor
torna-se uma quebra de linha real (utilizado pelas poucas mensagens de diálogo
com várias linhas). Editável diretamente se uma tradução precisar de correção, ou como
ponto de partida para outro idioma (adicione `language/<name>.lng`, adicione
`("<name>", "Native Name")` a `AVAILABLE_LANGUAGES` perto do topo de
`tester_config.py` e defina `"language": "<name>"` em `config.json`). Uma
chave em falta num ficheiro de idioma recorre a mostrar o próprio nome dessa chave
em vez de falhar, e um ficheiro de idioma em falta ou ilegível
(edição incorreta, nome de ficheiro errado) recorre ao inglês para toda a
interface - em ambos os casos a ferramenta continua utilizável enquanto a divergência
é resolvida.

**Configuração de SLCAN/SocketCAN no Linux** (reflash do adaptador, permissões da porta série,
ativação com `ip link`) é exatamente igual à secção 1 do flasher - consulte
o [README do próprio URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER),
secções 1 e 2, em vez de a duplicar aqui.

## 3. ⚙️ Como funciona

A janela está organizada em três colunas: a esquerda e o centro contêm as
secções sempre visíveis abaixo (1-4, depois 6), a direita contém o painel
por ferramenta da secção 5, que é a única parte da janela que realmente
muda consoante o que é detetado. Dividir as secções sempre visíveis
por duas colunas em vez de as empilhar todas numa só evita que a janela
cresça até deixar de caber num ecrã normal à medida que mais
destas secções foram sendo acrescentadas ao longo do tempo. O próprio painel de ferramenta da impressora 3D
(o mais alto dos 25) vai um passo além e divide os seus próprios controlos
em 2 subcolunas internamente, pela mesma razão. Consulte
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para a arquitetura ao nível dos módulos
que esta secção percorre.

**Connect** (secção 1, idêntica à do flasher): escolha Serial/SLCAN ou
SocketCAN, a porta/interface, opcionalmente deteta automaticamente o bitrate, depois
Connect.

**A deteção acontece automaticamente ao ligar** (ou clique em **Detect** para
a repetir): a ferramenta envia `0x110` (consultar ferramenta ativa) e `0x7F8` (consultar
versão), e usa a resposta para:
- Mostrar qual dos 25 perfis de ferramenta está ativo, e o estado global da
  placa (qualquer erro declarado, falha do barramento CAN, ainda no splash de arranque).
- Mostrar o HardwareID e a versão de firmware reportados, assinalando uma divergência
  se não corresponderem ao `THIS_HARDWARE_ID` deste projeto.
- Construir o painel **Tool Controls** à direita para essa ferramenta específica -
  e apenas essa ferramenta. Mudar a ferramenta configurada com jumpers e detetar
  novamente desmonta o painel antigo e constrói o novo de raiz.

**Global Controls** (secção 2, sempre visível independentemente da ferramenta
ativa): a substituição da cor do LED de estado, a cor e o
ligar/desligar do LED em anel, e o modo do ecrã OLED (`0x100`) - estes aplicam-se a todas as ferramentas, pelo que
não passam para o painel dinâmico. Especificamente no modo AOI Inspection,
o ligar/desligar do anel aqui é ignorado em favor do controlo de estroboscópio
próprio dessa ferramenta (segundo [docs/CANBUS.md](docs/CANBUS.md)) - a cor aplica-se em qualquer caso.

**Expansion Board** (secção 3, sempre visível): o barramento SPI genérico
e a linha DIAG0 de `CONN_EXPANSION` - a passagem direta em bruto que todas as variantes
de placa de expansão com driver partilham. Os sensores ADS1115 e MLX9064x,
e o driver do atuador de crimpagem, não são controlados
a partir daqui - vivem dentro do painel da sua própria ferramenta (Flying
Probe, Thermal Inspection, Crimping Actuator - consulte a secção 4
abaixo), uma vez que qual deles se aplica depende de qual perfil de ferramenta
está configurado com jumpers.

**Persistence F-RAM** (secção 4, também sempre visível, mas deliberadamente
separada da Expansion Board acima): a FM24CL64B partilha o barramento I2C2
de hardware do OLED - um componente central da placa, não algo ligado
a `CONN_EXPANSION` de todo. Agrupar as duas implicaria uma ligação entre elas
que não é real - o próprio conector de expansão não tem F-RAM, nem EEPROM,
nada não volátil.
- **SPI passthrough**: escreva bytes hexadecimais separados por espaços (1-7 deles, p. ex.
  `01 02 03`), prima Send e veja exatamente o que voltou em MISO durante
  essa mesma transferência (`0x180`/`0x181`) - um transporte de bytes em bruto, sem conhecimento
  dos registos do TMC5160, em linha com a abordagem do próprio firmware. Útil
  para exercitar o próprio barramento antes de compensar construir um painel dedicado
  para o protocolo de registos de uma placa de expansão específica.
- **DIAG0 level**: **Query DIAG0** lê o estado atual da linha de diagnóstico
  de stall/falha de um TMC5160 (`0x182`/`0x183`) - HIGH (inativa) ou LOW
  (ativa). Uma simples leitura por sondagem, não um valor em direto/enviado - prima
  o botão novamente para a atualizar.
- **Persistence F-RAM**: **Query State** lê de volta o que a placa
  guardou pela última vez antes de uma perda de energia (`0x190`/`0x191`) - qual era a ferramenta,
  o setpoint, se um erro crítico estava ativo nessa altura.
  **Erase F-RAM...** apaga-a (`0x192`, com uma caixa de diálogo de confirmação primeiro
  - isto não pode ser desfeito).
- **Expansion board type**: **Query** mostra qual das 7 possíveis
  configurações de `CONN_EXPANSION` está atualmente definida (`0x1A1` - consulte
  `EXPANSION.TXT`). Só de leitura aqui - defina-a antes a partir da secção CAN
  OTA do próprio `URTC Flasher`, uma vez que é um passo de configuração de hardware único,
  não algo a alterar descuidadamente a partir de uma ferramenta de diagnóstico em direto.
- **MLX9064x sensor variant**: **Query** mostra qual dos 3 membros da família
  MLX9064x (ou nenhum) está atualmente configurado (`0x1A7` -
  consulte `CANBUS.md`) - só tem significado quando o tipo de placa de expansão
  acima é uma variante Advanced ou Basic+MLX9064x. Só de leitura aqui, pela mesma
  razão que o tipo de placa de expansão acima.
- **Free tool configuration**: **Query** mostra a leitura em bruto dos jumpers de ID
  (0-31) juntamente com o que o registo `free_tool_selection` da F-RAM
  indica atualmente (`0x1A3` - consulte `EEPROM.TXT` secção 5) - só é realmente
  consultado por uma placa cujos jumpers leiam 0x1F/11111b. Só de leitura aqui,
  pela mesma razão que o tipo de placa de expansão acima - o `URTC Flasher` é a
  única ferramenta que o escreve.
- **Peripheral type & serial number**: **Query** mostra o tipo de periférico
  fixo (sempre URTC/0x03) juntamente com o número de série do dispositivo atualmente definido
  (`0x1A5` - consulte `EEPROM.TXT` secção 6), uma
  etiqueta atribuída pelo anfitrião para distinguir várias placas de outro modo idênticas no
  mesmo barramento CAN. Também só de leitura aqui - o `URTC Flasher` escreve o número de
  série, esta ferramenta limita-se a lê-lo de volta.

**Custom CAN Frame** (secção 6, também sempre visível): uma entrada de ID em bruto + bytes
hexadecimais com envio único e periódico - para um comando que ainda não
tem um controlo próprio aqui, ou para testar algo não (ou ainda não)
documentado em `docs/CANBUS.md`. Sem validação além do intervalo de ID e DLC≤8;
o que isto enviar é exatamente o que vai para o barramento. A mesma secção também
abre o **Raw Bus Monitor** (ver abaixo).

**Run Self-Test** (junto a Detect): executa um pequeno conjunto de verificações de comunicação
seguras e em repouso para a ferramenta atualmente detetada - confirma
que a consulta da ferramenta ativa e a consulta da versão respondem, depois (para ferramentas
com telemetria) envia um setpoint/velocidade/potência seguro de 0 e verifica se a
telemetria esperada chega. Deliberadamente nunca envia nada que
aqueça, dispare ou rode realmente com potência significativa - isto verifica que
o ciclo de comunicação funciona, não que um atuador responda fisicamente,
já que confirmar isso exige de qualquer forma uma pessoa a observar. Pede
confirmação antes de enviar o que quer que seja. As ferramentas sem telemetria (movimento
simples) ou puramente orientadas a eventos (scan probe) recebem uma
nota meramente informativa em vez de um verdadeiro aprovado/reprovado. **A cobertura é parcial**: apenas 7 das
25 ferramentas têm um passo de self-test definido (ferro de soldar, broca,
laser, impressora 3D, AOI, vácuo, scan probe) - as outras 18 ferramentas não
executam qualquer verificação quando este botão é premido.

**Gráficos de temperatura em direto**: os painéis do ferro de soldar e do bico da impressora 3D
mostram ambos um pequeno gráfico de linhas deslizante junto à sua
leitura de temperatura em direto - um simples Canvas do Qt Quick, não uma nova
dependência (matplotlib/pyqtgraph quebrariam a política de zero dependências desta ferramenta
para além de pyserial). Escala fixa do eixo Y (de 0 até ao teto de setpoint
da própria ferramenta) em vez de escala automática, para que a tendência seja fácil de ler
de relance, em vez de a escala mudar por baixo dela.

**Raw Bus Monitor** (aberto a partir da secção Custom CAN Frame): uma
janela separada que mostra todas as frames vistas, qualquer ID, independentemente do
painel da ferramenta ativa - uma tabela com deslocamento em direto (Time/ID/DLC/Data/Δt),
Pause/Clear, e uma leitura aproximada da carga do barramento/taxa de frames (atualizada
uma vez por segundo; o valor da carga não modela o overhead de bit-stuffing, por isso
trate-o como um valor de diagnóstico aproximado, não como uma medição certificada).
**Export .trc...**/**Export .asc...** guardam a tabela atualmente apresentada como um
ficheiro de rastreio simplificado ao estilo PEAK PCAN-View / Vector CANalyzer,
respetivamente - suficientemente próximo para ser legível pela maioria das ferramentas que esperam
esses formatos, sem garantia de ser idêntico byte a byte ao que as aplicações
reais produzem. Se `urtc_custom_ids.json` existir junto a este
script (opcional, não incluído por predefinição - `{"0x199": "My Sensor"}`),
a coluna de ID mostra esse nome amigável junto ao ID hexadecimal em bruto -
útil para quem testa o tráfego de uma placa de expansão personalizada
sem precisar de modificar o código-fonte desta ferramenta.

## 4. 🧰 Cobertura de ferramentas

Cada um dos 25 perfis tem o seu próprio painel, construído diretamente a partir de
`docs/CANBUS.md`:

| Ferramenta | Controlos | Telemetria em direto |
|---|---|---|
| Soldering Iron | Temperatura de setpoint, ligar/desligar; sentido do alimentador de fio + número de passos (único); consulta da posição do alimentador + reposição a 0 | Temperatura real; posição do alimentador (estimativa em malha aberta) |
| Paste/Liquid Dispenser, Screwdriver, both Grippers, SMT Pick & Place, Vacuum Gripper (LG) | Sentido + número de passos (movimento único) | nenhuma (0x120 partilhado, sem telemetria para nenhuma destas 7) |
| Vacuum Pickup | nenhum | Leitura analógica, peça detetada |
| Drill | Velocidade + sentido | RPM real, fim de curso |
| AOI Inspection | Modo do anel (desligado/estroboscópio/contínuo) + período do estroboscópio | Fim de curso |
| Laser Engraver | Potência + bloqueio do laser armar/seguro (uma saída do firmware, não um interlock de hardware) | Fim de curso |
| 3D Printer | Setpoint do bico, sentido/passos do extrusor, potência da ventoinha de camada, potência da ventoinha do hotend | Temperatura do hotend, RPM da ventoinha de camada, RPM da ventoinha do hotend |
| Scan Probe | nenhum | Contagem de eventos de impacto + marca temporal (prioridade máxima `0x095`) |
| Electromagnet | Caixa de seleção energizar/libertar | nenhuma |
| Spot Welder | Duração do pulso + Fire | nenhuma (só dispara se o sensor de contacto ler primeiro HIGH - consulte o próprio `0x1C0` de `docs/CANBUS.md`) |
| Conformal Coating, Press-Fit Inserter | nenhum - apenas painel informativo | nenhuma - ambos os IDs de ferramenta não têm qualquer handler CAN, o seu próprio atuador e sensor residem na placa principal do robô, consulte `docs/TOOLS.TXT` |
| Flying Probe | A leitura básica é automática; a leitura avançada precisa de uma palavra de configuração ADS1115 em bruto (hex) + Trigger Conversion + Read Result | Leitura básica do ADC integrado (automática, `0x243`) |
| UV Curing | Slider de potência (0-255) + Send/Off | nenhuma |
| Hot Air Rework | Temperatura de setpoint, potência do soprador, ligar/desligar | Temperatura em direto (partilha a telemetria `0x135` do ferro de soldar e o gráfico em direto - o mesmo ciclo térmico físico) |
| Crimping Actuator | Sentido + número de passos (movimento único, da mesma forma que as ferramentas de movimento partilhadas acima, mas chega ao driver de uma placa de expansão através de `0x1F0` em vez de `0x120` integrado) | nenhuma |
| Thermal Inspection | Trigger Capture, Check Status, Read Thermal Image | Canvas de mapa de calor de 32x24 píxeis (gradiente de azul a vermelho), obtido bloco a bloco por CAN a pedido - não é uma transmissão de vídeo em direto, consulte a secção 6 abaixo |
| Solder Paste Jetting | Canal PWM + frequência (Configure), depois duty + duração (Fire Pulse) | nenhuma |
| Ultrasonic Welder | Duração do pulso + Fire | nenhuma (mesma forma que o Spot Welder, mas sem controlo por sensor de contacto) |

**Os watchdogs de comunicação são tratados por si.** O ferro de soldar,
o Hot Air Rework (partilha o mesmo ciclo térmico e watchdog que o
ferro de soldar), o laser e o bico da impressora 3D têm cada um um watchdog de 250 ms
no firmware; a ventoinha de camada tem um de 1000 ms. Marcar a caixa
"Active" relevante não envia o comando apenas uma vez - reenvia-o
automaticamente (150 ms para as ferramentas com watchdog de 250 ms, 400 ms para a ventoinha
de camada) enquanto a caixa permanecer marcada, tal como um verdadeiro controlador
mestre tem de fazer. Desmarcá-la envia uma única frame de zero/desligado e
pára. A ventoinha do hotend não tem watchdog (tem antes um detetor de bloqueio - consulte
`docs/CANBUS.md`), pelo que é um simples envio único.

**Notas de conforto (comodidades de software, não funções de segurança).**

- **PARAR TODAS AS SAÍDAS** (em ambas as janelas, disponível com a ligação feita e as verificações ativas armadas) envia todos os comandos de desligar conhecidos - aquecedores, laser, berbequim, lâmpada UV, ventoinha de camada, libertação do eletroíman, motores de passo simples e crimpadora - seja qual for a ferramenta instalada, e pára todos os refrescamentos. A ventoinha do hotend fica ligada de propósito, porque o bico pode ainda estar quente. É um comando de software enviado pelo bus CAN, não uma paragem de emergência: não pode atuar se o bus, o adaptador, o PC ou a placa falharem.
- Os impulsos de soldadura únicos, o impulso de pasta e a crimpagem pedem confirmação também na janela clássica, como o deck Qt Quick faz sempre.
- O berbequim e a lâmpada UV são refrescados como o laser e os aquecedores. Enquanto o aquecedor da impressora 3D é mantido, o seu refrescamento de 150 ms leva 0 passos de extrusor, que o firmware lê como ordem de paragem: um movimento do extrusor iniciado nesse estado é cancelado em 150 ms, pelo que deve mover o extrusor com o aquecedor desligado até o firmware oferecer um modo que o deixe em paz.
- A porta e o débito são lembrados para a próxima sessão (`config.json`) e o deck Qt Quick tem o seu próprio seletor de débito. A **autodeteção** começa por apenas escutar a cada débito (nada é transmitido num barramento ativo) e só pergunta a cada débito quando o barramento está completamente silencioso.
- O Monitor de barramento em bruto pode ser limitado a alguns IDs CAN (**Filtro de ID**) e às tramas cujos dados mudaram (**Só alterações**).

### 🔥 Teste de bancada de thermal runaway (firmware URTC 0.3.2+ / 0.3.3+)

O Detect mostra agora *porquê* uma placa travou num erro: o byte 4 de `0x111` (proteção
contra thermal runaway: MAXTEMP, HEATING_NO_RISE ou DROPPED_AT_TARGET) é apresentado no
estado da placa, e um reset causado pelo watchdog de hardware (byte 5 de `0x111`) é
registado. **Thermal counters** (painel F-RAM em ambas as interfaces) lê `0x1AA`/`0x1AB`:
falhas térmicas ao longo da vida, total de horas de aquecedor ligado e a última falha. As respostas
de firmware mais antigo (`0x111` de 4 bytes, sem `0x1AB`) são reportadas como "not
reported", nunca como zero. O procedimento passo a passo para confirmar a proteção numa
placa real é [`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md).

## 5. 📋 Registos e pacotes de depuração

Tal como no flasher: um registo de sessão com marca temporal é escrito automaticamente
em `logs/` (pode ser apagado com segurança), e **Export Debug Bundle**
guarda um `.zip` com o registo atual apresentado no ecrã mais diagnósticos básicos do sistema
(SO, versão do Python, transporte/porta/bitrate atuais, ferramenta
detetada) para entregar a quem estiver a depurar um problema numa cabeça de ferramenta.

## 6. ⚠️ Limitações conhecidas

O contrato de evidência desta ferramenta - o que conta como aprovado/reprovado/desconhecido, porque
a ausência de evidência é sempre desconhecido e nunca aprovado, e porque não concede
qualquer autoridade própria de gravação de firmware - está documentado em
[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md).

- **Não testada com hardware real.** Cada peça aqui - a camada de
  transporte, o tratamento dos IDs CAN/disposição de bytes, a temporização do keepalive do watchdog -
  foi verificada isoladamente (frames simuladas, um subprocesso real para a temporização
  quando relevante), mas o ambiente que a construiu não tem acesso a USB.
  Trate uma primeira sessão real com a mesma cautela que o README do próprio
  flasher pede.
- **Um painel de ferramenta de cada vez, por design**, não é uma limitação atual a
  ser removida mais tarde - consulte a introdução acima para saber porquê.
- **As cores globais dos LEDs são uma substituição direta**, não uma leitura em direto -
  não há telemetria do que os LEDs de estado/anel estão realmente
  a mostrar, apenas do que foi comandado por último.
- **A imagem térmica da Thermal Inspection é obtida a pedido, não uma
  transmissão em direto.** Ler uma frame completa implica pedir todos os 48 blocos
  sequencialmente por CAN (no pior caso, a resolução do MLX90640/MLX90642) -
  isto pode demorar alguns segundos, e não existe modo de envio contínuo (streaming)
  no protocolo CAN desta ferramenta que o torne mais rápido. Primeiro é preciso acionar uma captura; Read Thermal Image espera então até dois segundos que o sensor indique que está pronto e, se não o fizer, não lê nada, porque o firmware não responde aos pedidos de bloco antes disso. Primeiro pergunta-se qual o sensor instalado (48 blocos para o MLX90640/MLX90642, 12 para o MLX90641), e um bloco perdido deixa os seus píxeis em branco em vez de deslocar o resto da imagem.
- **Run Self-Test só cobre 7 das 25 ferramentas** (ferro de soldar,
  broca, laser, impressora 3D, AOI, vácuo, scan probe) - consulte "Como
  funciona" acima para a explicação completa. As outras 18 ferramentas não recebem qualquer
  verificação automatizada desse botão; verificá-las continua a significar
  observar o hardware real a responder aos controlos do seu próprio painel.

## 📂 Estrutura do repositório

```
/
├── urtc_tester.py             Ponto de entrada - inicia o painel Qt Quick
├── qt_tester.py                Qt Quick front end - real default, read-only-by-default command deck
├── tester_config.py            Config/language/protocol constants (CAN IDs, tool
│                                names, MOTION_TOOL_IDS, AVAILABLE_LANGUAGES,
│                                EXPANSION_BOARD_TYPES)
├── tester_transports.py        SLCAN and SocketCAN transport classes
├── tester_bus_monitor.py       Background CAN read thread (CANBusMonitor)
├── tester_autodetect.py        Pesquisa da velocidade de um adaptador SLCAN
├── tester_selftest.py          Passos e execução do autoteste (sem código de janela)
├── tester_telemetry.py         Valores em direto de cada ferramenta e a série registada
├── tester_trace_export.py      Escrita das exportações de tramas .trc / .asc
├── urtc_ui/                    Auxiliares de interface partilhados (cópia do URTC-COMMON)
├── advanced_protocol.py        Pure CAN payload encoders for the migrated Qt
│                                Quick control families - hardware-free tests
├── verify_qt_custom_frame.py        Real, outside-tests/ end-to-end check of the Qt Quick Custom CAN Frame panel (needs a real Qt event loop)
├── verify_qt_telemetry_watch.py     Real, outside-tests/ end-to-end check of the Qt Quick telemetry watch (Vacuum Pickup / Scan Probe)
├── verify_qt_utility_panels.py      Real, outside-tests/ end-to-end check of the Qt Quick utility panels (Global Controls / Expansion Board / F-RAM)
├── verify_qt_selftest.py            Verificação real de ponta a ponta, fora de tests/, do autoteste Qt Quick
├── tests/
│   └── test_advanced_protocol.py   Hardware-free tests for advanced_protocol.py's encoders - run by CI, see Honesty check above
├── requirements.txt            pyserial>=3.5 + PySide6>=6.8,<7
├── build_exe.bat               Standalone Windows binary build script (PyInstaller)
├── build_exe.sh                Same, for Linux
├── build-test.bat              Non-versioning build/compile check
├── build-test.sh                Same, for Linux
├── bump.py                     Comando explícito para subir a versão (compilar nunca a sobe)
├── bump_version.py             Odometer-style version bump, run by the build scripts
├── bump_manifest_version.py    Syncs urtc.project.json's version to the native one (--sync)
├── URTC_Tester.spec            PyInstaller spec used by both build scripts
├── assets/
│   ├── URTC_APP_ICON.svg       Window/taskbar icon source (small standalone design)
│   ├── URTC_LOGO_TESTER.svg    Banner source (vector)
│   ├── HYDRA_UMC_ICON.svg      Maintained animated HYDRA-UMC vector source
│   ├── qml/
│   │   └── TesterDeck.qml      Qt Quick UI for the default command deck
│   ├── urtc_icon.ico           Windows icon, built from URTC_APP_ICON.svg
│   └── urtc_icon.png           Same, PNG form (Linux)
├── images/
│   ├── URTC_LOGO_TESTER.svg    Logo banner shown at the top of this README
│   └── URTC_TESTER_V1_1.png    Screenshot of the tool's main window (see Photos below)
├── language/
│   ├── english.lng             Default language, plain-text KEY=Value strings
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                       Session logs written here at runtime (safe to delete)
├── LICENSE                     Full license text - see License and Copyright
│                                Notices below
├── NOTICE                      Aviso de direitos de autor e licença da documentação
├── README.md                   This file
├── README_spa.md               Spanish translation
├── README_ita.md               Italian translation
├── README_fra.md               French translation
├── README_deu.md               German translation
├── README_zho.md               Chinese translation
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   ├── CANBUS.md
│   └── THERMAL_RUNAWAY_BENCH_TEST.md
├── tools/
│   ├── build_test.py                     Non-versioning build/compile check + Qt Quick deck source validation
│   └── ci_validate.py                    Manifest/CHANGELOG/docs validation used by CI
└── README_jpn.md               Japanese translation
```

## 📸 Fotografias

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="Janela do URTC Tester" width="700">
</p>

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, uma vez que um pedido pode, na verdade, dizer respeito a um destes e não a este repositório.

**Projeto principal**
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta sobre barramento CAN; o projeto principal do qual este repositório é uma ferramenta específica, dentro da sua própria família de ferramentas de barramento CAN.

**Projetos irmãos** — as outras ferramentas da própria família de ferramentas de barramento CAN do URTC
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta de gravação com GUI de desktop para placas URTC, CAN-OTA mais SWD/JTAG de chip completo.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem necessidade de instalação local.

**Diretamente relacionados**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de frota com um contrato de códigos de saída real e estável, um cliente em direto genuíno da API do próprio HYDRA-UMC-SERVER — executa auditorias a toda a frota (o comando `audit`) em todas as cabeças de ferramenta de uma só vez, indo além do âmbito de uma única placa que este tester cobre.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um verdadeiro companheiro de visão em Python para uma cabeça de ferramenta de inspeção térmica/RGB — complementa os diagnósticos CAN em direto deste projeto com as suas próprias verificações visuais de garantia de qualidade na cabeça de ferramenta.
- **[URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)** — ferramenta de ambiente de trabalho que deteta, instala e atualiza os repositórios da família URTC, uma ação explícita de cada vez.

**Também parte do ecossistema**

*Hardware e plataforma principais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível de Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, provisionamento de primeiro contacto por Wi-Fi.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptadores e validador para conectores de máquinas externas; estende a ideia de contrato do próprio SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend e clientes principais*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o verdadeiro backend headless (REST/WebSocket) com o qual todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel de controlo web com visualização 3D multirrobô em tempo real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame (PySide6) para desktop, para vários servidores em simultâneo, empacotado como executável autónomo.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação de controlo nativa para Android com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, incorporada no próprio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o próprio catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop, que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de alto nível do fluxo de placas para o pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — limite de coordenação seguro para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais sujeitos a portões.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub de integração do pipeline de visão Hailo-8, com uma verdadeira verificação de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carregamento por arquitetura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real + gerador de configuração MediaMTX com um verdadeiro limite de integração HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Nó de IA cognitiva (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub de integração do pipeline cognitivo Hailo-10 (orquestração de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analisador de intenções) com um relé Watch limitado e sujeito a confirmação.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre códigos de erro da MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF apenas com a biblioteca padrão sobre a documentação Markdown do próprio ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local e sujeito a políticas para o próprio ecossistema - observa, diagnostica e propõe correções; os dois níveis de risco mais elevados não estão deliberadamente implementados ainda.

*Orquestração e enxame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub de integração com um verdadeiro contrato de relatório de saúde gRPC/Protobuf e máquina de estados de missão.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila de tarefas real baseada em prioridades com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — watchdog real de saúde da frota baseado em gRPC com retry/backoff e deteção de divergência de identidade.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador de trajetórias 3D real baseado em RRT com validação real de colisões com obstáculos/espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para convergência multicélula.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub de integração do motor de gémeo digital, com um verdadeiro contrato de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedimental real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazenamento real de séries temporais assente em sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias com FFT + base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reproduzível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub de integração que retransmite para protocolos industriais, com uma verdadeira camada de lista de permissões de comandos/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão real de cliente de protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACLs de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reais MTConnect `/probe` e `/current` com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis Smart Summaries e Anomaly Highlighting sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware para um rack de montagem de placas com descodificação real de ID de ferramenta e lógica de pré-aquecimento Smart Idle.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta de desktop administrativa que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop Windows/Linux que constrói uma imagem CM5 pronta a gravar, pré-carregada com as versões mais atuais do ecossistema, com configuração de Wi-Fi/utilizador/SSH no primeiro arranque ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de edge de baixos privilégios recolhe um instantâneo sanitizado de inventário/saúde, um papel de control-plane apresenta-o em modo só de leitura e pede a um fornecedor de IA que sugira um diagnóstico - nunca aplica um patch nem implementa nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que armazena o código-fonte do ecossistema e executa tarefas de compilação/teste limitadas sob uma fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

## 📜 LICENÇA

O URTC Tester é (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso tem de
ser incluído em quaisquer distribuições deste projeto ou de obras derivadas.

Este projeto é composto por código-fonte e pela sua própria documentação, disponibilizados
sob licenças diferentes - cada uma adequada ao que realmente
abrange:

1. O código-fonte (`urtc_tester.py` e todos os módulos `tester_*.py`)
   e qualquer binário construído a partir dele através de `build_exe.bat`/`build_exe.sh`
   estão disponíveis sob a **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.
   Texto completo em https://www.gnu.org/licenses/gpl-3.0.html.

2. A documentação (este README e as suas próprias traduções -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md` e os guias de `docs/`)
   está disponível sob **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texto completo em
   https://creativecommons.org/licenses/by-sa/4.0/.

Esta ferramenta é o companheiro de diagnóstico CAN em direto do projeto
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- consulte o repositório desse projeto para o firmware da placa,
os desenhos de hardware e a documentação completa do protocolo contra o qual esta ferramenta
é exercitada. O firmware do próprio URTC é GPL-3.0-or-later e os seus desenhos de hardware são
CERN-OHL-S v2; a licença desta ferramenta aqui não se estende a esse
projeto separado, e vice-versa. Existe também uma alternativa baseada na web que cobre
um âmbito semelhante em
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Se construir sobre este projeto, tenha presente a divisão de licenças: as alterações ao código
devem manter-se GPL-3.0-or-later, os derivados da documentação devem manter-se CC
BY-SA - cada um com atribuição a este projeto e ao seu autor.

---

## 📚 Documentação e comunidade

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como reportar uma vulnerabilidade, e as áreas de foco de segurança reais deste projeto.
- **[SUPPORT.md](SUPPORT.md)** — onde colocar questões e reportar erros.
- **[LICENSE.md](LICENSE.md)** — a licença própria deste projeto.

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
