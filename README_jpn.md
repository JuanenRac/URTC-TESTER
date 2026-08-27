<p align="center">
  <img src="/images/URTC_LOGO_TESTER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester（Windows / Linux）

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  🇯🇵 <b>日本語</b>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Tkinter-lightgrey.svg" alt="Tkinter">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>


**バージョン：** 0.1.0 · **作者：** JuanenRac（Electro Hobby 3D）&lt;electrohobby3d@gmail.com&gt;

ライセンス：ソースコードは **GPL-3.0**、本ドキュメントは **CC BY-SA 4.0**——
本リポジトリの `LICENSE`、または本ドキュメント末尾の「ライセンスと著作権
表示」セクションを参照してください。

URTC ボード向けのライブ CAN バステスターです。フラッシャーが使用するのと
同じ USB-CAN アダプター経由で接続し、ボードに現在 25 種類のツールプロファ
イルのうちどれにジャンパー設定されているかを尋ね、そのツール自身のコント
ロールとテレメトリのみを表示します——1 つのウィンドウで 25 個すべてを表現
しようとするのではありません。ここで行うことはすべて、現在実行中のアプリ
ケーションに対するランタイムコマンドまたはテレメトリの読み取りです。フ
ラッシュには一切触れないため、これによってボードが開始時より動作しなく
なることはありません。

## 1. 🆚 フラッシャーとの関係

本ツールと [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) は
同じトランスポート層を共有しています（SLCAN と SocketCAN のクラスは同一
です）。どちらも最終的には同じ種類のアダプターとの間で CAN フレームを
やり取りする必要があるだけですが、両者が行う仕事は根本的に異なります：

| | フラッシャー | テスター |
|---|---|---|
| フラッシュに触れる | はい（それがすべての目的） | 決してない |
| 通信対象 | 主にブートローダー | 実行中のアプリケーション |
| 目的 | ファームウェアの更新 | ツールヘッドの実際のハードウェアをテスト/検証 |

どちらが必要かわからない場合：ボードがすでにファームウェアを実行してい
て、あるツールが実際に動作するか（ヒーターが温まる、モーターが回る、
LED が点灯する）を確認したいなら、これが必要なものです。

## 2. 📦 インストールと実行

フラッシャーと同じパターンです：

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

または独立したバイナリをビルドします：Windows では `build_exe.bat`、
Linux では `./build_exe.sh`。どちらも最初に `build/`/`dist/` をクリーン
にし、`assets/`（バナーとアイコン）を実行ファイルにバンドルします——
これらのスクリプトの背後にあるより詳しい理由はフラッシャー自身の README
を参照してください。ここでも同様に当てはまります。

**バージョン管理：** `TESTER_VERSION`（`tester_config.py` 内、タイトル
バー、About ダイアログ、セッションログ、デバッグバンドルに表示）は
`MAJOR.MINOR.PATCH` に従います。両方のビルドスクリプトは、`bump_version.py`
を通じて、実際のビルドのたびに自動的にこれを加算します。10 進法の
「オドメーター」方式です：PATCH +1、PATCH が 9 を超えると MINOR へ繰り
上がります（例：`0.1.9` → `0.2.0`）。ソースから実行する場合
（`python urtc_tester.py`）はこれに一切触れません——実際の
`build_exe.bat`/`build_exe.sh` の実行だけがそうします。MAJOR は自動的
には決して加算されず、手動でのみ変更されます。バージョン履歴は
`CHANGELOG.md` を参照してください。

**起動時**、バナーはメインウィンドウが表示される前に 5 秒間画面中央に
表示され、ウィンドウ自体の内部には存在しません——フラッシャーと同じで、
理由も同じです（ウィンドウ自体をコンパクトに保つため）。ウィンドウ/
タスクバーのアイコンも同様に、縮小されたバナーではなく、小さな独立した
デザインです。

### メニューバー

- **ファイル** —— ログを保存（画面上のログをプレーンテキストとして；
  システム診断情報を含む、より完全なバンドルについては、代わりに下記の
  「ログとデバッグバンドル」を参照）、そして終了。
- **言語** —— 5 つの利用可能な言語を切り替えます（翻訳の仕組みについて
  は上の「言語」を参照）。
- **ヘルプ** —— Readme（本ファイルを読み取り専用のビューアーウィンドウ
  で開きます；現在の言語向けの翻訳版が存在すれば自動的にそれを使用しま
  す）、URTC GitHub（プロジェクトのリポジトリをブラウザで開きます）、
  ライセンス（本ツールの GPL-3.0 ライセンス、リポジトリ自身の
  `LICENSE` ファイルから読み込まれます）、そしてこのアプリについて
  （バージョンと作者）。

### ファイル構成

本ツールは可読性のためだけに、責務ごとにモジュールへ整理されています
——それらを別々のファイルとして持つことと、1 つの大きなファイルとして
持つこととの間に、機能的な違いはありません。完全なファイルごとの内訳
は、本ドキュメント末尾近くの「📂 リポジトリ構成」セクションを参照して
ください。

**言語**：デフォルトは英語です。メインウィンドウ内のドロップダウンでは
なく、（ウィンドウ上部のメニューバー内の）**言語**メニューから切り替え
ます——インターフェース（ラベル、ボタン、ダイアログ、ログメッセージ）
を 5 つの利用可能な言語のいずれかへ切り替え、即座に本ツールの隣にある
`config.json` に保存され、次回起動時に適用されます。翻訳は `language/`
下のプレーンテキストファイル（`english.lng`、`spanish.lng`、
`italian.lng`、`french.lng`、`german.lng`）として、シンプルな
`KEY=Value` ペア、1 行に 1 つの形式で存在します——`#` で始まる行と空行
は無視され、値の中のリテラルな `\n` は実際の改行になります（数個の
複数行ダイアログメッセージで使用されています）。翻訳の修正が必要な場合
は直接編集できますし、他の言語を追加する際の出発点としても使えます
（`language/<name>.lng` を追加し、`tester_config.py` の先頭付近の
`AVAILABLE_LANGUAGES` に `("<name>", "現地語名")` を追加し、
`config.json` に `"language": "<name>"` を設定します）。言語ファイル
に存在しないキーは、クラッシュするのではなく、そのキー自身の名前をその
まま表示するようにフォールバックし、欠落した、または読み取れない言語
ファイル（誤った編集、間違ったファイル名）は、インターフェース全体を
英語にフォールバックします——いずれの場合も、不一致が解決されるまで
ツールは使用可能なままです。

**Linux SLCAN/SocketCAN のセットアップ**（アダプターの再フラッシュ、
シリアル権限、`ip link` の立ち上げ）は、フラッシャーの第 1 節とまった
く同じです——ここで重複させるのではなく、[URTC Flasher 自身の
README](https://github.com/JuanenRac/URTC-FLASHER) の第 1 節と第 2 節
を参照してください。

## 3. ⚙️ 仕組み

ウィンドウは 3 列にレイアウトされています：左列と中央列には下記の常に
表示されるセクション（第 1-4 節、そして第 6 節）が入り、右列には第 5
節のツールごとのパネルが入ります。これはウィンドウの中で検出内容に応じ
て実際に変化する唯一の部分です。常に表示されるセクションを 1 列に積み
重ねるのではなく 2 列に分割することで、これらのセクションが時間ととも
に増えるにつれてウィンドウが通常の画面に収まらないほど高くなることを
防いでいます。3D プリンター自身のツールパネル（25 個中最も高いもの）
は、同じ理由でさらに進んで、自身のコントロールを内部的に 2 つのサブ
列に分割しています。

**接続**（第 1 節、フラッシャーとまったく同じ）：シリアル/SLCAN または
SocketCAN、ポート/インターフェースを選び、任意でビットレートを自動検出
し、それから接続します。

**検出は接続時に自動的に行われます**（または**検出**をクリックしてやり
直せます）：本ツールは `0x110`（現在のツールを照会）と `0x7F8`
（バージョンを照会）を送信し、その応答を使って以下を行います：
- 25 種類のツールプロファイルのうちどれがアクティブか、そしてボードの
  全体的な状態（何らかの宣言されたエラー、CAN バス障害、まだ起動スプ
  ラッシュ中かどうか）を表示します。
- 報告された HardwareID とファームウェアバージョンを表示し、それが
  本プロジェクト自身の `THIS_HARDWARE_ID` と一致しない場合はフラグを
  立てます。
- その特定のツール——そしてそのツールのみ——向けの**ツール制御**パネル
  を右側に構築します。ジャンパー設定されているツールを切り替えて再度
  検出すると、古いパネルが解体され、新しいパネルがゼロから構築されます。

**グローバル制御**（第 2 節、どのツールがアクティブであっても常に表示）：
ステータス LED の色のオーバーライド、リング LED の色とオン/オフ、そして
OLED 表示モード（`0x100`）——これらはすべてのツールに適用されるため、
動的パネルには移動しません。特に AOI 検査モードでは、ここでのリングの
オン/オフは無視され、代わりにそのツール自身のストロボ制御が優先されます
（`docs/CANBUS.TXT` による）——色はいずれにせよ引き続き適用されます。

**拡張ボード**（第 3 節、常に表示）：`CONN_EXPANSION` 自身の汎用 SPI
バスと DIAG0 ライン——ドライバーを搭載するすべての拡張ボードバリアント
が共有する生のパススルーです。ADS1115 と MLX9064x センサー、そして圧接
アクチュエーター自身のドライバーは、ここから制御されるのではなく、それ
ぞれ自身のツール自身のパネル内に存在します（フライングプローブ、サーマ
ル検査、圧接アクチュエーター——下記の第 4 節参照）。これらのうちどれが
実際に適用されるかは、ジャンパー設定されているツールプロファイルに依存
するためです。

**永続化 F-RAM**（第 4 節、これも常に表示、ただし上記の拡張ボードとは
意図的に分離）：FM24CL64B は OLED 自身のハードウェア I2C2 バスを共有
します——これはコアなボードコンポーネントであり、`CONN_EXPANSION` に
配線されているものではまったくありません。この 2 つをグループ化すると、
実際には存在しない両者の間の接続を暗示してしまいます——拡張コネクタ自体
には F-RAM も EEPROM も、不揮発性のものは何もありません。
- **SPI パススルー**：スペース区切りの16進数バイト（1〜7 個、例：
  `01 02 03`）を入力し、送信を押すと、同じ転送中に MISO 上で返ってきた
  内容がそのまま表示されます（`0x180`/`0x181`）——生のバイト伝送であり、
  TMC5160 のレジスタを認識するものではなく、ファームウェア自身のアプ
  ローチと一致しています。特定の拡張ボードのレジスタプロトコル向けに
  専用パネルを構築する価値が出る前に、バス自体をテストするのに便利です。
- **DIAG0 レベル**：**DIAG0 を照会**は、TMC5160 の失速/障害診断ライン
  （`0x182`/`0x183`）の現在の状態を読み取ります——HIGH（非アクティブ）
  または LOW（アサート済み）。単純なポーリング読み取りであり、リアル
  タイム/プッシュされる値ではありません——更新するにはもう一度ボタンを
  押してください。
- **永続化 F-RAM**：**状態を照会**は、電源喪失前にボードが最後に保存し
  た内容を読み戻します（`0x190`/`0x191`）——それがどのツールだったか、
  設定値、当時重大エラーがアクティブだったかどうか。**F-RAM を消去...**
  はそれを消去します（`0x192`、まず確認ダイアログが表示されます——この
  操作は取り消せません）。
- **拡張ボードタイプ**：**照会**は、7 つの可能な `CONN_EXPANSION` 構成
  のうち現在設定されているものを表示します（`0x1A1`——`EXPANSION.TXT`
  参照）。ここは読み取り専用です——代わりに `URTC Flasher` 自身の CAN
  OTA セクションから設定してください。これは一度限りのハードウェア構成
  ステップであり、ライブの診断ツールから気軽に変更するものではないため
  です。
- **MLX9064x センサーバリアント**：**照会**は、3 つの MLX9064x ファミリ
  メンバー（またはまったくなし）のうち現在設定されているものを表示しま
  す（`0x1A7`——`CANBUS.TXT` 参照）——上記の拡張ボードタイプが Advanced
  バリアントまたは Basic+MLX9064x の場合にのみ意味を持ちます。ここも
  読み取り専用で、理由は上記の拡張ボードタイプと同じです。
- **自由工具構成**：**照会**は、生の ID ジャンパー読み取り値（0-31）と、
  F-RAM の `free_tool_selection` レジスタが現在示している内容
  （`0x1A3`——`EEPROM.TXT` 第 5 節参照）を並べて表示します——ジャンパー
  が 0x1F/11111b を示すボードでのみ実際に参照されます。ここも読み取り
  専用で、理由は上記の拡張ボードタイプと同じです——それを書き込む唯一の
  ツールは `URTC Flasher` です。
- **周辺機器タイプ & シリアル番号**：**照会**は、固定の周辺機器タイプ
  （常に URTC/0x03）を、現在設定されているデバイスシリアル番号
  （`0x1A5`——`EEPROM.TXT` 第 6 節参照）と並べて表示します。これは、
  同じ CAN バス上で複数の（それ以外は同一の）ボードを区別するための、
  ホストが割り当てるラベルです。ここも読み取り専用です——`URTC Flasher`
  がシリアル番号を書き込み、本ツールはそれを読み戻すだけです。

**カスタム CAN フレーム**（第 6 節、これも常に表示）：一次的送信と周期
的送信の両方に対応した、生の ID + 16進数バイトの入力欄です——ここに
まだ独自のコントロールがないコマンドや、`docs/CANBUS.TXT` にまだ
（あるいはまったく）記載されていないものをテストするのに便利です。
ID の範囲と DLC≤8 以外の検証はありません。ここで送信するものがそのまま
バス上に送出されます。同じセクションから**生のバスモニター**も開けます
（下記参照）。

**自己診断を実行**（検出の隣）：現在検出されているツールに対して、安全
で静止状態の通信チェックの小さなセットを実行します——現在のツール照会
とバージョン照会の両方が応答することを確認し、その後（テレメトリを持つ
ツールについては）安全な設定値/速度/出力 0 を送信し、期待されるテレメト
リが届くことを確認します。意味のある出力で実際に加熱、発射、または回転
するものは意図的に一切送信しません——これは通信の往復が機能することを
検証するものであり、アクチュエーターが物理的に反応することを検証する
ものではありません。それを確認するにはいずれにせよ人間の観察が必要だか
らです。何かを送信する前に確認を求めます。テレメトリのないツール（単純
な動作）や純粋にイベント駆動のツール（スキャンプローブ）は、実際の合格/
不合格ではなく、情報のみの注記を得ます。**カバレッジは部分的です**：
25 種類のツールのうち、定義された自己診断ステップを持つのは 7 種類のみ
です（はんだごて、ドリル、レーザー、3D プリンター、AOI、バキューム、
スキャンプローブ）——このボタンが押されたとき、他の 18 種類のツールは
チェックを一切実行しません。

**リアルタイム温度グラフ**：はんだごてと 3D プリンターノズルのパネルは
どちらも、そのリアルタイム温度読み取り値の隣に小さなスクロール折れ線
グラフを表示します——単純な Tkinter Canvas ウィジェットであり、新しい
依存関係ではありません（matplotlib/pyqtgraph は、本ツールの pyserial
を超えたゼロ依存ポリシーを破ってしまいます）。自動スケーリングではなく
固定の Y 軸スケール（0 からそのツール自身の設定値の上限まで）なので、
軸が下でずれ動くのではなく、一目で傾向を読み取りやすくなっています。

**生のバスモニター**（カスタム CAN フレームセクションから開く）：現在の
ツールパネルとは独立して、見えたすべてのフレーム、任意の ID を表示する
独立したウィンドウです——ライブスクロールするテーブル（時刻/ID/DLC/
データ/Δt）、一時停止/クリア、そしておおよそのバス負荷/フレームレート
の読み取り値（1 秒ごとに更新；この負荷の数値はビットスタッフィングの
オーバーヘッドをモデル化していないため、認証された測定値ではなく、大ま
かな診断値として扱ってください）。**エクスポート .trc...**/**エクス
ポート .asc...** は、現在表示されているテーブルをそれぞれ簡略化された
PEAK PCAN-View / Vector CANalyzer 風のトレースファイルとして保存します
——それらの形式を期待するほとんどのツールで読み取れる程度には十分近い
ものですが、実際のアプリケーションが生成するものとバイト単位で同一で
あることは保証されません。本スクリプトの隣に `urtc_custom_ids.json`
が存在する場合（任意、デフォルトでは含まれない——
`{"0x199": "My Sensor"}`）、ID 列は生の 16 進数 ID の隣にそのわかりやす
い名前を表示します——本ツールのソースを変更する必要なく、カスタム拡張
ボード自身のトラフィックをテストする人にとって便利です。

## 4. 🧰 ツールカバレッジ

25 種類のプロファイルのそれぞれが、`docs/CANBUS.TXT` から直接構築され
た独自のパネルを持ちます：

| ツール | コントロール | リアルタイムテレメトリ |
|---|---|---|
| はんだごて | 設定温度、オン/オフ；送りワイヤーフィーダー方向 + ステップ数（ワンショット）；フィーダー位置照会 + 0 へのリセット | 実際の温度；フィーダー位置（オープンループ推定値） |
| ペースト/液体ディスペンサー、ドライバー、両方のグリッパー、SMT ピック＆プレース、大判真空グリッパー | 方向 + ステップ数（ワンショット移動） | なし（0x120 を共有、これら 7 つすべてでテレメトリなし） |
| 真空ピックアップ | なし | アナログ読み取り値、部品検出 |
| ドリル | 速度 + 方向 | 実際の回転数、エンドストップ |
| AOI 検査 | リングモード（オフ/ストロボ/連続）+ ストロボ周期 | エンドストップ |
| レーザー彫刻機 | 出力 + インターロック有効化/安全 | エンドストップ |
| 3D プリンター | ノズル設定値、エクストルーダー方向/ステップ数、レイヤーファン出力、ホットエンドファン出力 | ホットエンド温度、レイヤーファン回転数、ホットエンドファン回転数 |
| スキャンプローブ | なし | 衝撃イベント回数 + タイムスタンプ（最優先度 `0x095`） |
| 電磁石 | 励磁/解放チェックボックス | なし |
| スポット溶接機 | パルス持続時間 + 発射 | なし（接触センサーが先に HIGH を読み取った場合にのみ発射——`docs/CANBUS.TXT` 自身の `0x1C0` 参照） |
| コンフォーマルコーティング、プレスフィットインサーター | なし——情報表示パネルのみ | なし——両方のツール ID には CAN ハンドラーがまったくなく、その自身のアクチュエーターとセンサーはロボット自身のメインボード上にある、`docs/TOOLS.TXT` 参照 |
| フライングプローブ | 基本読み取りは自動；高度な読み取りには生の ADS1115 設定ワード（16進数）+ 変換トリガー + 結果読み取りが必要 | 基本的なオンボード ADC 読み取り（自動、`0x243`） |
| UV 硬化 | 出力スライダー（0-255）+ 送信/オフ | なし |
| ホットエアリワーク | 設定温度、ブロワー出力、オン/オフ | リアルタイム温度（はんだごて自身の `0x135` テレメトリとリアルタイムグラフを共有——同じ物理的熱制御ループ） |
| 圧接アクチュエーター | 方向 + ステップ数（ワンショット移動、上記の共有動作ツールと同じ形状だが、板載の `0x120` の代わりに `0x1F0` 経由で拡張ボード自身のドライバーに到達） | なし |
| サーマル検査 | キャプチャトリガー、状態確認、サーマル画像読み取り | 32x24 ピクセルのヒートマップキャンバス（青から赤へのグラデーション）、要求に応じて CAN 経由でチャンクごとに取得——ライブビデオフィードではありません、下記の第 6 節参照 |
| はんだペースト噴射 | PWM チャンネル + 周波数（設定）、その後デューティ + 持続時間（パルス発射） | なし |
| 超音波溶接機 | パルス持続時間 + 発射 | なし（スポット溶接機と同じ形状だが、接触センサーのゲートなし） |

**通信ウォッチドッグはあなたに代わって処理されます。** はんだごて、
ホットエアリワーク（はんだごてと同じ熱制御ループとウォッチドッグを
共有）、レーザー、そして 3D プリンターノズルはそれぞれファームウェア
内に 250ms のウォッチドッグを持っています；レイヤーファンは 1000ms
のものを持っています。関連する「アクティブ」ボックスをチェックすると、
コマンドを一度送信するだけでなく——そのボックスがチェックされている
限り（250ms ウォッチドッグのツールでは 150ms、レイヤーファンでは
400ms）、実際のマスターコントローラーがそうしなければならないのと同じ
方法で自動的に再送信します。チェックを外すと、単一のゼロ/オフフレーム
を送信して停止します。ホットエンドファンにはウォッチドッグがありません
（代わりに失速検出器——`docs/CANBUS.TXT` 参照）ので、単純なワンショット
送信です。

## 5. 📋 ログとデバッグバンドル

フラッシャーと同じです：タイムスタンプ付きのセッションログが自動的に
`logs/`（削除しても安全）に書き込まれ、**デバッグバンドルをエクスポー
ト**は、現在の画面上のログに加えて基本的なシステム診断情報（OS、Python
バージョン、現在のトランスポート/ポート/ビットレート、検出されたツール）
を `.zip` として保存し、ツールヘッドの問題をデバッグしている人へ渡せ
ます。

## 6. ⚠️ 既知の制限事項

- **実際のハードウェアに対してテストされていません。** ここにあるすべ
  ての部分——トランスポート層、CAN ID/バイトレイアウトの処理、ウォッチ
  ドッグのキープアライブのタイミング——は独立して確認されました（モック
  化されたフレーム、関連する箇所ではタイミング用の実際のサブプロセス）
  が、これを構築した環境には USB アクセスがありません。フラッシャー
  自身の README が求めているのと同じ注意をもって、最初の実際のセッシ
  ョンに臨んでください。
- **設計上、一度に 1 つのツールパネル**であり、後で取り除かれるべき現在
  の制限ではありません——理由は上記の導入部を参照してください。
- **グローバル LED の色は単純なオーバーライドです**、リアルタイムの
  読み戻しではありません——ステータス/リング LED が実際に現在何を表示
  しているかについてのテレメトリはなく、最後に指令された内容のみです。
- **サーマル検査自身のサーマル画像はプル型であり、ライブフィードでは
  ありません。** 完全なフレームを読み取るには、CAN 経由で全 48 個の
  チャンクを順次要求する必要があります（最悪の場合、MLX90640/MLX90642
  自身の解像度）——これには数秒かかる可能性があり、より速くするための
  ストリーミングプッシュモードは本ツール自身の CAN プロトコルにはあり
  ません。サーマル画像読み取りが実際のデータを返す前に、キャプチャが
  すでにトリガーされ、準備完了と報告されている必要があります（状態確
  認）——早すぎるタイミングで読み取ると、センサー自身のバッファが最後
  に保持していたものが何であれ、それが描画されるだけです。
- **自己診断の実行は 25 種類のツールのうち 7 種類のみをカバーします**
  （はんだごて、ドリル、レーザー、3D プリンター、AOI、バキューム、
  スキャンプローブ）——完全な説明は上記の「仕組み」を参照してください。
  他の 18 種類のツールは、このボタンから自動チェックを受けません；
  それらを検証するには、依然としてそれぞれ自身のパネルのコントロール
  に対する実際のハードウェアの反応を観察する必要があります。

## 📂 リポジトリ構成

```
/
├── urtc_tester.py             エントリポイント——CLI なしの起動とスプラッシュ画面
├── tester_config.py            設定/言語/プロトコル定数（CAN ID、ツール名、
│                                MOTION_TOOL_IDS、AVAILABLE_LANGUAGES、
│                                EXPANSION_BOARD_TYPES）
├── tester_transports.py        SLCAN と SocketCAN のトランスポートクラス
├── tester_bus_monitor.py       バックグラウンド CAN 読み取りスレッド（CANBusMonitor）
├── tester_gui_core.py          TesterGUI コア——接続、検出、ウィンドウの
│                                ライフサイクル、そしてメニューバー；
│                                下記 3 つのミックスインが組み合わさる
│                                クラス
├── tester_common_panels.py     CommonPanelsMixin——グローバル/F-RAM/拡張/
│                                自己診断/バスモニター/カスタムフレーム
│                                パネル（常に表示されるセクション）
├── tester_panel_helpers.py     PanelHelpersMixin——すべてのツールパネル
│                                ビルダーが使用する共有ユーティリティ
├── tester_tool_panels.py       ToolPanelsMixin——25 種類のツールプロファ
│                                イルすべてをカバーする 19 個のツール固有
│                                パネルビルダー（複数のツールが 1 つの
│                                ビルダーを共有します。例えば
│                                `_build_motion_panel` はそれだけで
│                                そのうちの 7 つをカバーします）
├── requirements.txt            単一の依存関係：pyserial>=3.5
├── build_exe.bat               独立 Windows バイナリビルドスクリプト（PyInstaller）
├── build_exe.sh                同上、Linux 向け
├── URTC_Tester.spec            両方のビルドスクリプトが使用する PyInstaller の spec
├── assets/
│   ├── URTC_APP_ICON.svg       ウィンドウ/タスクバーアイコンのソース（独立した小型デザイン）
│   ├── URTC_LOGO_TESTER.svg    起動バナーのソース
│   ├── urtc_icon.ico           Windows アイコン、URTC_APP_ICON.svg から構築
│   ├── urtc_icon.png           同上、PNG 形式（Linux）
│   └── urtc_tester_banner.png  起動バナー PNG、上記の SVG からレンダリング
├── images/
│   ├── URTC_LOGO_TESTER.svg    本 README の先頭に表示される Logo バナー
│   └── URTC_TESTER_V1_1.png    本ツールのメインウィンドウのスクリーンショット（下記の写真を参照）
├── language/
│   ├── english.lng             デフォルト言語、プレーンテキストの KEY=Value 文字列
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   └── german.lng
├── logs/                       実行時のセッションログがここに書き込まれる（削除しても安全）
├── LICENSE                     完全なライセンステキスト——下記のライセンスと著作権表示を参照
├── README.md                   本ファイル
├── README_spa.md               スペイン語翻訳
├── README_ita.md               イタリア語翻訳
├── README_fra.md               フランス語翻訳
└── README_deu.md               ドイツ語翻訳
```

## 📸 写真

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="URTC Tester window" width="700">
</p>

## 🔗 関連プロジェクト

本プロジェクトは、同一著者（JuanenRac / Electro Hobby 3D）による、ファームウェア、制御アプリ、AI ノード、産業統合にまたがる多数のプロジェクトからなる、より大きなロボティクスエコシステムの一部です。ご要望が実際にはこれらのプロジェクトのいずれかに関するものであり、本リポジトリのものではない可能性もあるため、知っておく価値があります。

### 本プロジェクトと直接関連

- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 本テスターがカバーする単一ボードの範囲を超えて、すべてのツールヘッドに対して一度に車両群全体の監査（`audit` コマンド）を実行します。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — ツールヘッドに対する独自の視覚的品質保証（QA）チェックで、本プロジェクトのライブ CAN バス診断を補完します。

### エコシステムのその他のプロジェクト

**💠 Core Ecosystem**
[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC) · [HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER) · [HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) · [HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE) · [HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI) · [HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL) · [HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL) · [HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF) · [URTC](https://github.com/JuanenRac/URTC) · [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) · [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)

**👁️ Vision AI Node (Hailo-8)**
[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE) · [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER) · [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF) · [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES) · [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)

**🧠 Cognitive AI Node (Hailo-10)**
[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) · [HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE) · [HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI) · [HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER) · [HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)

**🐝 Orchestration & Swarm**
[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR) · [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC) · [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D) · [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER) · [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)

**🎮 Digital Twin & Simulation**
[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN) · [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA) · [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE) · [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)

**📊 Data & Analytics**
[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE) · [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR) · [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR) · [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)

**🏭 Industrial Gateway**
[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL) · [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER) · [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER) · [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)

**🛠️ Complementary Tools**
[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) · [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH) · [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

## 📜 ライセンスと著作権表示

URTC Tester の著作権は (c) 2026 JuanenRac（Electro Hobby 3D）に帰属します。本プロジェクトまたはその派生物を配布する際は、この表示を必ず含めてください。

本プロジェクトはソースコードとそれ自身のドキュメントで構成されており、それぞれ実際にカバーする内容に適した異なるライセンスの下で提供されています：

1. ソースコード（`urtc_tester.py` および各 `tester_*.py` モジュール）と、`build_exe.bat`/`build_exe.sh` を通じてそこから構築されるあらゆるバイナリは、**GNU General Public License v3.0（GPL-3.0）** の下で提供されます。全文は https://www.gnu.org/licenses/gpl-3.0.html を参照してください。

2. ドキュメント（本 README およびその自身の翻訳版——`README_spa.md`、`README_ita.md`、`README_fra.md`、`README_deu.md`）は、**クリエイティブ・コモンズ 表示-継承 4.0 国際（CC BY-SA 4.0）** の下で提供されます。全文は https://creativecommons.org/licenses/by-sa/4.0/ を参照してください。

本ツールは [URTC（Universal Robot Tool Controller）](https://github.com/JuanenRac/URTC) プロジェクトのライブ CAN バス診断コンパニオンです——本ツールがテスト対象としているボードファームウェア、ハードウェア設計、完全なプロトコルドキュメントは、同プロジェクト自身のリポジトリを参照してください。URTC 自身のファームウェアは GPL-3.0 であり、そのハードウェア設計は CERN-OHL-S v2 です。本ツール自身のここでのライセンスはその独立したプロジェクトには及ばず、その逆も同様です。類似の範囲をカバーする Web ベースの代替案も、[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO) に存在します。

本プロジェクトを基に開発を行う際は、このライセンス区分を念頭に置いてください：コードの変更は GPL-3.0 を維持し、ドキュメントの派生物は CC BY-SA を維持してください——いずれも本プロジェクトおよびその作者への帰属表示を伴う必要があります。

## 👤 作者

**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 🛠️ BUILD & RUN

リリースビルドの前に、バージョンを変更しないビルドチェックを使用してください。

| 操作 | Windows | Linux / macOS |
|---|---|---|
| ビルドチェック（バージョンと CHANGELOG を変更しない） | `build-test.bat` | `./build-test.sh` |
| 実行 / 開発（提供されている場合） | `run*.bat` または `dev*.bat` | `./run*.sh` または `./dev*.sh` |

`build-test.bat` と `build-test.sh` は、`hydra-umc.project.json` をインクリメントせず、`CHANGELOG.md` も変更せずにプロジェクトのスタックをコンパイルまたは検証します。通常のコンパイラ出力だけが作成される場合があります。既存の `build*.bat`、`build*.sh`、`run*`、`dev*` は、各プロジェクト固有のバージョン化または実行時の動作を維持します。その動作が必要な場合はそれらを使用してください。