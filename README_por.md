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

### Um testador de barramento CAN em direto para a placa URTC: mostra apenas os controlos e a telemetria da cabeça de ferramenta ligada

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-633-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>

---

**Verificação de honestidade - o que realmente funciona hoje:** os codificadores de payload CAN para as famílias de controlo Qt Quick migradas (`advanced_protocol.py`) são reais e estão cobertos pelos testes de `tests/` (`python -m pytest -q`). O CI deste repositório (`.github/workflows/ci.yml`) também os executa, juntamente com `ruff check`, `python -m mypy`, `tools/ci_validate.py`, uma compilação de sintaxe de cada ficheiro `.py` e os quatro scripts `verify_qt_*.py`, pelo que uma regressão aí faz falhar a compilação. Os quatro scripts `verify_qt_*.py` na raiz do repositório (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) são verificações end-to-end reais, deliberadamente fora de `tests/`, contra um transporte simulado com entrega real de Signals entre threads - os quatro passam com `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, que o CI também executa. Esse é o limite honesto do que é verificado automaticamente: a camada de transporte, o tratamento dos IDs CAN/disposição de bytes e a lógica da ponte Qt Quick são reais e exercitados com frames simuladas, não com hardware real - como as "Limitações conhecidas" abaixo já indicam, isto foi construído sem acesso a USB, pelo que nada aqui foi ainda verificado numa placa real. `qt_tester.py` e `assets/qml/TesterDeck.qml` são a implementação real e substancial (milhares de linhas no total), exercitada pelos testes com placas simuladas e pelos scripts de verificação, e nunca por uma placa real.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado e ainda não existe nenhuma placa URTC montada. Os bootloaders verificam as imagens de firmware com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica (prevista); as imagens de aplicação publicadas estão assinadas com a chave pública de desenvolvimento (`signing_key_kind: dev`), pelo que qualquer pessoa pode produzir uma imagem que o bootloader aceita; nada foi transmitido a uma placa real. Leia a [base de segurança](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.4.5` |
| Maturidade | Funcional |
| Testes | 633 (`python -m pytest -q`) |
| Tecnologia | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Destino | O PC de quem o usa |
| Em hardware real | Só simulado: testado com emuladores, dublês de teste ou simuladores; não há registo de execução em hardware real para esta versão |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Funcionalidades](#-funcionalidades) · [Segurança](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Estrutura](#-estrutura-do-repositório) · [Relacionados](#-projetos-relacionados)

<!-- urtc-section:status_tester -->
## 🚦 Estado do projeto

🟢 feito e verificado · 🟡 funciona, com limites conhecidos · 🟠 a meio ou por verificar · 🔴 por fazer ou a não funcionar. Nada é verde se nunca correu em hardware real.

| Parte | Estado | O que o repositório consegue demonstrar |
| --- | :---: | --- |
| Software | 🟡 | Funciona num PC e contra o simulador; nunca foi usado com uma placa real. |
| Interface | 🟡 | A janela funciona e é verificada contra uma placa simulada; não foi experimentada com um adaptador real. |
| Testes | 🟢 | A bateria de testes passa na CI em cada envio. |
| Hardware real | 🟠 | Ainda não correu numa placa real: o ensaio de bancada continua pendente. |
| Documentação | 🟡 | README em oito línguas e documentos de referência; as traduções não foram revistas por falantes nativos. |

<!-- /urtc-section:status_tester -->

## 🎯 Visão geral

Um exercitador de barramento CAN em tempo real para a placa URTC. Liga-se através do mesmo
adaptador USB-CAN que o flasher utiliza, pergunta à placa para qual dos seus 25 perfis de
ferramenta está atualmente configurada com jumpers e mostra apenas os controlos e a telemetria
dessa ferramenta - não uma janela a tentar representar as 25 ao mesmo tempo. Tudo o que faz é
um comando em tempo de execução ou uma leitura de telemetria sobre a aplicação atualmente em
execução; nunca toca na flash, pelo que nada aqui pode deixar a placa menos funcional do que
estava ao início.

### Relação com o flasher

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

## 🧩 Papel no URTC

O URTC-TESTER é o programa que verifica o que uma cabeça de ferramenta URTC realmente faz enquanto executa a sua aplicação: liga-se pelo mesmo adaptador USB-CAN do URTC-FLASHER, pergunta à placa para qual dos seus 25 perfis de ferramenta está configurada com jumpers e mostra apenas os controlos e a telemetria dessa ferramenta, nunca uma janela que tente representar as 25. Tudo o que faz é um comando em execução ou uma leitura de telemetria; nunca toca na flash, pelo que não pode deixar uma placa pior do que a encontrou. O protocolo que fala é o do URTC-COMMON, e o URTC-WEB-STUDIO oferece os mesmos fluxos num navegador.

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="Arquitetura de URTC-TESTER: quem o usa, o que contém e de que depende" width="100%">
</p>

Como as partes deste repositório se encaixam: quem o usa, o que contém e de que depende. A imagem é desenhada a partir de `docs/architecture.json` e verificada com o código.

<!-- urtc-section:updates -->
### Como se atualiza

Este programa pode procurar uma versão mais recente de si próprio: o botão «Procurar atualizações» pergunta uma vez ao GitHub e só propõe um pacote assinado se for para o seu sistema e mais recente. Nada é verificado nem instalado por si só, a não ser que ative a verificação, e uma atualização precisa da sua confirmação. O pacote tem de coincidir com o seu SHA-256 e com a assinatura da chave das versões fixada no programa; a versão anterior é guardada e reposta sozinha se a nova não arrancar. `urtc-updater --cli package list|check|install|rollback` faz o mesmo na linha de comandos para o flasher e o tester, e `install --file` funciona sem rede.
<!-- /urtc-section:updates -->

## 🖼️ Capturas de ecrã

<!-- urtc-shots -->
Capturadas a 1920×1080 numa bancada de testes, com dados de exemplo e sem qualquer instalação real por trás.

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="A janela ao abrir: a porta de transporte, o modo seguro só de escuta, os perfis de ferramenta e os pontos de controlo de identidade e saúde." width="100%"><br><sub>A janela ao abrir: a porta de transporte, o modo seguro só de escuta, os perfis de ferramenta e os pontos de controlo de identidade e saúde.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="Cabeças de ferramenta no barramento: um barramento modelado com seis cabeças, cada uma num estado possível (selecionada, conflito de endereço, falha retida, no bootloader, perdida e pronta)." width="100%"><br><sub>Cabeças de ferramenta no barramento: um barramento modelado com seis cabeças, cada uma num estado possível (selecionada, conflito de endereço, falha retida, no bootloader, perdida e pronta).</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="A janela de Ajuda: os passos para utilizar o programa, escritos no idioma da janela." width="100%"><br><sub>A janela de Ajuda: os passos para utilizar o programa, escritos no idioma da janela.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="A janela de atualizações: um pacote assinado mais recente só é instalado depois de o confirmar." width="100%"><br><sub>A janela de atualizações: um pacote assinado mais recente só é instalado depois de o confirmar.</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

**Registador de falhas, funções opcionais, bancada do rack e vista térmica (novo, verificado apenas com simulações):** o painel lê a caixa negra da placa (`0x1A8` / `0x1A9`) e guarda-a em CSV e JSON, automaticamente uma vez por cada erro indicado pela placa quando essa opção está ativa; liga as funções opcionais do firmware (`0x1AE` / `0x1AF`, desligadas por predefinição, com efeito após o próximo arranque); tem um rack de ferramentas simulado com o protocolo série do URTC-SMART-RACK, a identidade de cada cabeça (tipo e número de série) e a exportação de uma página de estado; e mostra a imagem de inspeção térmica em falsa cor (uma imagem simulada di-lo). Os nomes e tipos das ferramentas vêm agora dos perfis de ferramenta partilhados do URTC-COMMON. Nada disto foi usado com uma placa real.

**PID do aquecedor (novo, verificado só com simulações):** o painel lê o estado do PID do aquecedor do firmware (`0x1B9` / `0x1BA`: os ganhos em vigor, o estado e a saída do último ciclo de controlo), guarda ganhos (de 0 a 600) e inicia ou cancela o autoajuste por relé, que aquece a ponta em torno do ponto de regulação atual do ferro de soldar (100 a 445 C) e guarda os ganhos encontrados. Guardar ganhos e iniciar o autoajuste pedem a confirmação habitual; cancelar não. A cabeça simulada da linha de comandos (`--transport simulate`) também responde a estas tramas. A função tem de ser ativada antes, entre as funções opcionais; nada disto foi usado com uma placa real.

Estas imagens são a janela real, desenhada sem ecrã tal como abre (nada ligado, nada enviado). O guia percorre o painel, a janela de Ajuda e a de atualização.

[Guia com imagens](docs/WINDOW_GUIDE.md)

## ✨ Funcionalidades

### Como funciona

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

### Cobertura de ferramentas

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

#### 🔥 Teste de bancada de thermal runaway (firmware URTC 0.3.2+ / 0.3.3+)

O Detect mostra agora *porquê* uma placa travou num erro: o byte 4 de `0x111` (proteção
contra thermal runaway: MAXTEMP, HEATING_NO_RISE ou DROPPED_AT_TARGET) é apresentado no
estado da placa, e um reset causado pelo watchdog de hardware (byte 5 de `0x111`) é
registado. **Thermal counters** (painel F-RAM em ambas as interfaces) lê `0x1AA`/`0x1AB`:
falhas térmicas ao longo da vida, total de horas de aquecedor ligado e a última falha. As respostas
de firmware mais antigo (`0x111` de 4 bytes, sem `0x1AB`) são reportadas como "not
reported", nunca como zero. O procedimento passo a passo para confirmar a proteção numa
placa real é [`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md).

<!-- urtc-section:heads -->
### Várias cabeças de ferramenta num barramento

O firmware pode fazer várias cabeças de ferramenta partilharem um barramento CAN (a extensão multinó). Vem **desativada por defeito**, e um barramento com uma só cabeça funciona exatamente como antes. A janela **Cabeças** encontra as cabeças, lista cada uma com o seu endereço, ferramenta e número de série, e mostra o seu estado: pronta, selecionada, conflito de endereço, falha retida, no seu bootloader ou perdida. Seleciona uma, o programa pede confirmação e só depois lhe envia alguma coisa; enquanto houver várias cabeças no barramento, um comando é recusado até uma estar selecionada e o ter confirmado. Se a cabeça selecionada se perder, todas as cabeças passam ao estado seguro (uma caixa da janela desativa-o). Só foi testada contra um modelo do barramento, não com placas. Veja `docs/MULTINODE.md` em URTC-COMMON.
<!-- /urtc-section:heads -->

<!-- urtc-section:bus_scenarios -->
### Falhas do barramento simulado

Um plano ou uma atualização pode ser executado contra um barramento simulado que se porta mal como um real, sem hardware. Um cenário é um ficheiro JSON (`urtc-scenario/1`) que lista as falhas: tramas perdidas, repetidas, reordenadas, atrasadas, perdidas em rajadas ou cortadas, um nó que se cala ou recusa uma ordem e diz porquê, e uma cabeça em configuração livre (`0x1F`) que responde a `0x1A3` e `0x1A2` de maneiras diferentes. Nada muda se não o pedir: a opção é `--scenario FICHEIRO` (com a cabeça simulada do tester ou o transporte mock do flasher), o ficheiro é verificado com rigor e recusado se algo não for compreendido, e um adaptador real nunca o aceita. O mesmo cenário com a mesma semente dá as mesmas tramas na mesma ordem, e `bus_scenario.py generate --seed N` escreve cenários de teste que combinam as falhas. A execução deixa o registo de evidência habitual (`urtc-evidence/1`), que diz que o barramento era uma simulação e com que cenário e semente. Um cenário pode retirar tramas, repeti-las ou movê-las, mas não pode fazer um nó dizer que algo funcionou. Formato e regras: [Cenários do barramento](https://github.com/JuanenRac/URTC-COMMON/blob/main/docs/BUS_SCENARIOS.md).
<!-- /urtc-section:bus_scenarios -->

<!-- urtc-section:evidence_report -->
### Relatório de evidências

Os registos de evidência de uma pasta (`urtc-evidence/1`) podem ser transformados num relatório para anexar a uma compilação ou a um processo de validação: `python urtc_tester.py --headless report --evidence-dir PASTA --out FICHEIRO [--format html|pdf] [--language NOME]` (se não for indicado, o formato segue a extensão do ficheiro), ou o botão **Relatório** da janela Histórico, que escreve `evidence_report.html` e `evidence_report.pdf` na pasta. O relatório tem um resumo, uma linha e uma secção por registo, o resultado da verificação de cada um e uma marca clara que diz se o registo é SIMULADO, uma reprodução de um traço, de um adaptador real ou não o diz. Um registo que não passa a verificação aparece como NÃO VÁLIDO com o motivo e nunca é omitido; o código de saída é 1 se algum não for válido, e o relatório é escrito na mesma. O HTML é um só ficheiro sem scripts nem recursos externos, todo o texto de um registo é escapado, e o PDF é escrito pelo próprio programa (o texto ocidental com um tipo de letra padrão e o chinês e o japonês com um subconjunto incorporado do Noto Sans CJK, ao abrigo da SIL Open Font License 1.1; o HTML conserva todos os carateres). Os mesmos registos dão os mesmos bytes. Um resumo que coincide mostra que um registo não foi alterado depois de escrito, não quem o escreveu, e a marca de adaptador real só significa que não é indicada simulação: nada disto correu numa placa real. Detalhes: [Registos de evidência](https://github.com/JuanenRac/URTC-COMMON/blob/main/docs/EVIDENCE.md).
<!-- /urtc-section:evidence_report -->

## 🔒 Segurança e proteção

| Risco | Defesa |
|---|---|
| Uma ordem enviada a uma placa que não é a ferramenta que a janela mostra | O painel de uma ferramenta só é mostrado para a ferramenta que a própria placa comunicou, e cada comando está condicionado por uma correspondência de identidade |
| Transmitir sem querer | A janela arranca em modo só de escuta: não pode transmitir até as verificações ativas serem armadas deliberadamente, e cada ação que atua sobre a placa pede primeiro uma confirmação na janela |
| Danificar a placa | O testador nunca toca na flash: tudo o que faz é um comando em execução ou uma leitura de telemetria contra a aplicação que está a funcionar |
| Um registo que alguém pudesse alterar | A exportação da sessão é um zip com o registo, um manifesto que o nomeia pelo seu SHA-256 e os diagnósticos do sistema |

Nada disto foi experimentado numa placa real e nada é uma função de segurança certificada; veja as limitações abaixo.

## 🔌 Interfaces

Tal como no flasher: um registo de sessão com marca temporal é escrito automaticamente
em `logs/` (pode ser apagado com segurança), e **Export Debug Bundle**
guarda um `.zip` com o registo atual apresentado no ecrã mais diagnósticos básicos do sistema
(SO, versão do Python, transporte/porta/bitrate atuais, ferramenta
detetada) para entregar a quem estiver a depurar um problema numa cabeça de ferramenta.

### 🤖 Sem janela: planos de teste

`python urtc_tester.py --headless COMANDO` executa o tester sem janela, para uma linha de produção, um script de bancada ou uma tarefa de CI: `info` (quem responde: ferramenta, firmware, estado rápido), `selftest`, `run-plan FICHEIRO` e `validate-plan FICHEIRO`. Um plano é um pequeno ficheiro JSON de passos guardado em `plans/` (esperar uma ferramenta, sem falhas, uma versão mínima de firmware, o autoteste, uma trama cujo valor esteja num intervalo, uma espera, uma pergunta à pessoa na bancada). O comando escreve um registo de cada trama e um registo de resultado que nomeia o registo pelo seu SHA-256, o mesmo do painel. Um plano só envia consultas, a menos que diga `"actuation": true` e o operador acrescente `--allow-actuation`; as tramas do bootloader, de atualização, de configuração e de apagamento nunca são enviadas, um comando que o firmware abandona se não for refrescado (um aquecedor, um berbequim, um laser) pode ser repetido enquanto o plano espera (`keepalive_ms`), e depois de um plano que ordenou algo todas as saídas são desligadas de novo. `--transport simulate` reproduz uma cabeça simulada e `--transport replay --port FICHEIRO` um traço `.trc` ou `.asc` gravado, para que um plano possa ser experimentado sem placa. Código de saída: 0 passou, 1 uma verificação falhou, 2 o plano ou os argumentos estão errados, 3 o teste não pôde ser realizado. O texto que imprime está em inglês, como a linha de comandos do flasher. Pormenores em [`docs/HEADLESS.md`](docs/HEADLESS.md). Nada disto foi executado contra uma placa real.

**Planos na janela (novo, verificado só com testes e a cabeça simulada):** a secção PLANOS DE TESTE, no fim da coluna direita do deck, lista os planos de `plans/`, executa o que escolher contra a placa ligada com o mesmo motor (não no modo só escuta e só enquanto nada mais ler o barramento), mostra cada passo assim que termina, faz numa caixa de diálogo as perguntas de um passo de confirmação e guarda o log e o registo do resultado. Um plano que comanda saídas pede antes uma confirmação e no fim todas as saídas são desligadas; Cancelar pára-o depois do passo em curso.

**Procurar atualizações.** O botão «Procurar atualizações» pergunta ao GitHub uma vez pela versão mais recente e só propõe a transferência se esta tiver um pacote para este sistema mais recente do que a versão instalada. O pacote só é aceite se o SHA-256 e a assinatura Ed25519 (a chave das versões, fixada no programa) forem válidos; só é instalado depois de o confirmar, nunca enquanto uma saída estiver ligada, e a versão anterior é guardada para poder voltar atrás (e é reposta sozinha se a nova não arrancar). Nada é verificado nem instalado por si só: a verificação ao abrir é uma opção, desligada por defeito, e a confirmação só se desliga na mesma janela, depois de um aviso.

**Reproduzir um rastreio gravado.** «Abrir rastreio» carrega um rastreio `.trc` ou `.asc` (os que o monitor do barramento exporta, ou de PCAN-View e CANalyzer) e reproduz as suas tramas recebidas numa lista própria, marcadas como REPLAY, de 0,25x a 10x, com pausa, paragem e repetição; um silêncio de mais de dois segundos é encurtado. Uma reprodução nunca transmite, nunca responde a um pedido, nunca se mistura com o monitor do barramento nem com a sua exportação, e não arranca enquanto uma placa estiver ligada (pausa sozinha se ligar uma). Um ficheiro com mais de 50 MB ou sem tramas recebidas é recusado e diz-se.

**Visualizador da caixa negra.** O registo lido da placa, e qualquer registo guardado antes (`.json` ou `.csv` escritos por este programa, abertos com «Abrir um registo guardado», sem placa), é desenhado como a temperatura medida e o valor pretendido ao longo do tempo, com uma marca onde o indicador de erro foi levantado pela primeira vez, e listado amostra a amostra com os indicadores por extenso. Cada campo tem de ser um número inteiro dentro do intervalo e um registo tem no máximo 67 amostras; um ficheiro que não é um registo é recusado com o motivo e o desenho anterior mantém-se.

**Sem hardware:** uma placa virtual faz as vezes do adaptador e da placa. Execute `python -m urtc_can.virtual_board` e indique o seu URL série como porta (`--transport serial --port socket://127.0.0.1:7777`); a placa responde à consulta de versão e ao estado rápido como uma aplicação, pelo que `info` e os planos de consultas correm de ponta a ponta sem nada ligado. É um modelo escrito a partir da descrição do protocolo, não uma cabeça de ferramenta: o autoteste de uma ferramenta informa o que não consegue ler.

- **Histórico das operações.** O botão **Histórico**, junto de Ajuda, abre os registos de evidência (`urtc-evidence/1`) que o URTC-TESTER escreveu na sua pasta de registos. Cada linha mostra o tipo, o resultado, a ferramenta, a placa e as versões, da mais recente para a mais antiga; um registo editado depois de escrito, um ficheiro que não é JSON ou um registo de outro formato é apresentado como não válido, com o que está errado. A lista pode ser filtrada por resultado e por texto ou reduzida aos registos que falham; lê a pasta de cada vez que abre, mostra no máximo 500 linhas (e indica quantas há) e não altera nada no disco. É a mesma janela no URTC-FLASHER, no URTC-TESTER e no URTC-UPDATER, partilhada a partir do URTC-COMMON, nos oito idiomas. Na linha de comandos, `python urtc_tester.py --headless history [FOLDER] [--json]` lista os registos de uma pasta, verifica cada um e termina com o estado 1 se algum não for válido; não abre nenhum bus.

- **Ficheiro de identificadores próprios.** O `urtc_custom_ids.json` tem de conter um objeto JSON (`{"0x199": "O meu sensor"}`); um ficheiro que contenha uma lista, ou qualquer outro conteúdo inválido, é ignorado com um aviso e o programa arranca com os nomes incorporados.

- **Linhas do plano de testes e bancada do rack.** Cada mensagem que um passo de um plano de testes dá (sem resposta, ferramenta errada, firmware demasiado antigo, valor fora do intervalo, confirmação do operador...) é mostrada na língua da janela; o registo, o registo de resultado e a linha de comandos mantêm o texto em inglês. A bancada simulada do rack responde a cada ordem com a sua trama de resposta (uma confirmação, ou uma recusa com o motivo: comprimento errado, sem ferramenta na ranhura, temperatura acima do limite, ferramenta inválida, sem aquecedor, retida por chegar cedo demais, comando desconhecido), lê-a e diz o motivo na língua da janela; uma segunda ordem para uma ferramenta antes do intervalo mínimo é retida como faz o firmware.

## 🚀 Início rápido

O mesmo padrão do flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

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
com várias linhas). Gerados a partir do catálogo do URTC-COMMON (uma tradução corrige-se lá e os ficheiros são escritos de novo, nunca à mão), ou como ponto de partida para outro idioma (adicione `language/<name>.lng`, adicione
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

<!-- urtc-section:compatibility -->
### Requisitos e compatibilidade

As versões dos programas URTC que funcionam em conjunto, e a versão do protocolo que cada uma fala, constam da tabela de compatibilidade que o URTC-COMMON gera: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md). As notas de uma versão dos repositórios que incluem `tools/changelog_section.py` (o firmware, o flasher, o tester e o updater) são a secção do CHANGELOG dessa versão seguida desta tabela: `python tools/changelog_section.py VERSION --compat`.
<!-- /urtc-section:compatibility -->

## 🧪 Testes

O conjunto tem 633 testes (`python -m pytest -q`; com Qt numa máquina sem ecrã, `QT_QPA_PLATFORM=offscreen`; os que precisam do PySide6 são ignorados sem ele): os codificadores e descodificadores de carga CAN de cada família de ferramentas, os transportes SLCAN e SocketCAN contra simulações, a sonda de identidade, o autoteste, os reenvios de vigilância, a verificação de saúde do barramento, os planos de teste e o modo sem janela, a exportação da sessão com o seu hash, os ficheiros de idioma e os painéis Qt Quick. Quatro scripts na raiz (`verify_qt_*.py`) comandam os painéis Qt Quick de ponta a ponta com um ciclo de eventos Qt real. A CI executa também `ruff check`, `python -m mypy` e `tools/ci_validate.py`. Nada disto correu contra uma placa real.

## 🏗️ Compilação e publicação

Ou crie um binário autónomo: `build_exe.bat` no Windows, `./build_exe.sh`
no Linux. Ambos limpam primeiro `build/`/`dist/` e incluem `assets/` (o
banner e o ícone) no executável - consulte
[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md) para o percurso de validação
`build-test.bat`/`build-test.sh`, que não altera a versão e sobre o qual estes scripts de empacotamento
se constroem, e o README do próprio flasher para o raciocínio mais completo por detrás
dos próprios scripts de empacotamento, uma vez que se aplica aqui de forma idêntica.

**Versão:** `TESTER_VERSION` (em `tester_config.py`, mostrada na barra de título, na caixa Acerca de, nos registos de sessão e nos pacotes de depuração) segue `MAJOR.MINOR.PATCH` e só sobe com o passo explícito `python bump.py`. Executar a partir do código (`python urtc_tester.py`) e compilar (`build_exe.bat` / `build_exe.sh`) nunca lhe tocam. Veja `CHANGELOG.md` para o histórico de versões.

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Estrutura do repositório URTC-TESTER" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
URTC-TESTER/
├── urtc_tester.py                                     ponto de entrada
├── qt_tester.py                                       o painel Qt Quick
├── tester_*.py                                        transportes, monitor, autoteste, planos, telemetria
├── advanced_protocol.py                               codificadores puros de cargas CAN
├── verify_qt_*.py                                     verificações de ponta a ponta dos painéis Qt
├── urtc_can/                                          protocolo, transportes e atualizações (cópia)
├── urtc_ui/                                           auxiliares de interface (cópia)
├── tests/                                             um ficheiro de testes por área
├── plans/                                             planos de teste de exemplo (JSON)
├── language/                                          os oito ficheiros de idioma .lng
├── assets/                                            QML, faixa e ícone
├── docs/                                              arquitetura, compilação e execução
├── logs/                                              registos de sessão (fora do Git)
├── tools/                                             verificação de compilação e ferramentas partilhadas
├── images/                                            faixa e imagens deste README
├── .github/                                           fluxo de CI e modelos de issues e pull requests
├── test.sh test.bat                                   executam os testes
├── run.sh run.bat                                     arrancam o programa
├── build-test.sh build-test.bat                       scripts de compilação e testes que não alteram nada no repositório
├── urtc.project.json                                  manifesto: versão, papel, maturidade e comando de compilação
├── CHANGELOG.md                                       o que mudou em cada versão
├── SECURITY.md SUPPORT.md LICENSE                     política de segurança, suporte e licença
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 como contribuir e código de conduta
├── .gitattributes .gitignore                          definições do Git
├── build_exe.sh build_exe.bat                         programa autónomo (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   scripts que sobem a versão
├── requirements*.txt requirements*.lock               dependências, com os seus bloqueios
├── mypy.ini ruff.toml .coveragerc                     definições de tipos, lint e cobertura
├── urtc_i18n.lock.json                                bloqueio dos ficheiros de idioma gerados
└── NOTICE LICENSE.md                                  aviso de direitos de autor e licença da documentação
```

</details>

A lista anotada de cada ficheiro de código, uma linha por ficheiro, está em [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Roteiro e limites conhecidos

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

## 🌍 Idiomas

O README e os textos existem em inglês, espanhol, francês, italiano, alemão, chinês, japonês e português europeu.

## 🔗 Projetos relacionados

O URTC é feito de repositórios independentes, cada um com a sua versão, os seus testes e o seu README. Esta é a família, por grupos:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware da placa da cabeça de ferramenta (25 perfis de ferramenta, bootloader CAN) e a referência do protocolo CAN.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - o protocolo CAN escrito uma só vez como dados (especificação, tabelas geradas, vetores de conformidade) e o código que os programas partilham.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - ferramenta de ambiente de trabalho que atualiza o firmware da placa por CAN ou por SWD/JTAG.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - gateway à frente do barramento CAN: só deixa passar os identificadores de uma lista, limita a sua taxa e pede uma chave de sessão.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - lógica em C independente do hardware e protocolo de comandos para um suporte de ferramentas com pré-aquecimento e acompanhamento do ciclo de vida.
  * **URTC-TESTER** (este repositório) - testador de ambiente de trabalho do barramento CAN em direto que mostra os controlos e a telemetria do perfil de ferramenta que uma placa reporta.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - protocolo de tramas de sensor em C e um companheiro em Python térmico/RGB para uma cabeça de ferramenta de inspeção.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - aplicação de navegador que grava e testa a placa por Web Serial e SLCAN, sem instalar nada.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - as ferramentas de repositório partilhadas da família como um conjunto com versão e um ficheiro de bloqueio que distingue uma cópia editada de uma desatualizada.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - arquitetura, interfaces, base de segurança e catálogo gerado do ecossistema, mais as ferramentas que comparam todos os repositórios.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - ferramenta de ambiente de trabalho que deteta, instala e atualiza os repositórios da família URTC, uma ação explícita de cada vez.

**Projetos irmãos (independentes, com a mesma base e as mesmas ferramentas):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - projeto irmão: o centro de documentação do HYDRA-UMC, um ecossistema independente que partilha a base e as ferramentas com este
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - projeto irmão: o centro de documentação do A.R.M.O.R., o ecossistema de segurança, também independente e sobre a mesma base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - o perfil e o painel de estado de todos os ecossistemas

## 📚 Documentação

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como reportar uma vulnerabilidade, e as áreas de foco de segurança reais deste projeto.
- **[SUPPORT.md](SUPPORT.md)** — onde colocar questões e reportar erros.
- **[LICENSE.md](LICENSE.md)** — a licença própria deste projeto.

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `URTC_CI=1 python tools/ci_validate.py`: tem de passar. Veja [CONTRIBUTING.md](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).
* O README existe em oito idiomas: uma alteração ao texto faz-se nos oito ficheiros, e as secções partilhadas com outros repositórios são escritas por `tools/readme_sections.py` do URTC-COMMON.
* Uma alteração ao protocolo CAN começa no URTC-COMMON (`spec/can_protocol.json`) e chega a este repositório através da cópia verificada.
* Não descreva como a funcionar numa placa aquilo que só foi compilado.
* Comunique uma vulnerabilidade em privado: [SECURITY.md](SECURITY.md). Perguntas, ideias e relatórios: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA

Licença: **GPL-3.0-or-later** para o código-fonte, **CC BY-SA 4.0** para esta
documentação - consulte `LICENSE` neste repositório, ou a secção "License and
Copyright Notices" no final deste documento.

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
