"""
One-shot translator for XYrminal .ts files.

Reads i18n/xyrminal_en.ts as the source template, and writes
i18n/xyrminal_<lang>.ts with translations filled in from the
TRANSLATIONS dictionary below.

Usage:
    python tools_translate_ts.py

After running, compile .qm files:
    pyside6-lrelease i18n/xyrminal_ru.ts -qm i18n/xyrminal_ru.qm
    ... and so on for the other languages.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
I18N_DIR     = PROJECT_ROOT / "i18n"
TEMPLATE     = I18N_DIR / "xyrminal_en.ts"

LANGS = ["ru", "be", "de", "fr", "zh", "ja", "ko"]


T: dict[str, dict[str, str]] = {

    "&Logs": {
        "ru": "&Журналы", "be": "&Журналы", "de": "&Protokolle",
        "fr": "&Journaux", "zh": "&日志",    "ja": "&ログ",     "ko": "&로그",
    },
    "Save log": {
        "ru": "Сохранить журнал", "be": "Захаваць журнал", "de": "Protokoll speichern",
        "fr": "Enregistrer le journal", "zh": "保存日志", "ja": "ログを保存", "ko": "로그 저장",
    },
    "Save log as…": {
        "ru": "Сохранить журнал как…", "be": "Захаваць журнал як…",
        "de": "Protokoll speichern unter…", "fr": "Enregistrer le journal sous…",
        "zh": "日志另存为…", "ja": "ログを名前を付けて保存…", "ko": "다른 이름으로 로그 저장…",
    },
    "Open logs folder": {
        "ru": "Открыть папку журналов", "be": "Адкрыць папку журналаў",
        "de": "Protokollordner öffnen", "fr": "Ouvrir le dossier des journaux",
        "zh": "打开日志文件夹", "ja": "ログフォルダを開く", "ko": "로그 폴더 열기",
    },
    "&View": {
        "ru": "&Вид", "be": "&Выгляд", "de": "&Ansicht",
        "fr": "&Affichage", "zh": "&视图", "ja": "&表示", "ko": "&보기",
    },
    "&Setting": {
        "ru": "&Настройки", "be": "&Налады", "de": "&Einstellungen",
        "fr": "&Paramètres", "zh": "&设置", "ja": "&設定", "ko": "&설정",
    },
    "Theme": {
        "ru": "Тема", "be": "Тэма", "de": "Design",
        "fr": "Thème", "zh": "主题", "ja": "テーマ", "ko": "테마",
    },
    "Terminal text color": {
        "ru": "Цвет текста терминала", "be": "Колер тэксту тэрмінала",
        "de": "Textfarbe des Terminals", "fr": "Couleur du texte du terminal",
        "zh": "终端文字颜色", "ja": "ターミナル文字色", "ko": "터미널 텍스트 색상",
    },
    "Language": {
        "ru": "Язык", "be": "Мова", "de": "Sprache",
        "fr": "Langue", "zh": "语言", "ja": "言語", "ko": "언어",
    },
    "&Help": {
        "ru": "&Справка", "be": "&Даведка", "de": "&Hilfe",
        "fr": "&Aide", "zh": "&帮助", "ja": "&ヘルプ", "ko": "&도움말",
    },
    "Info": {
        "ru": "Информация", "be": "Інфармацыя", "de": "Info",
        "fr": "Informations", "zh": "信息", "ja": "情報", "ko": "정보",
    },
    "About XYrminal": {
        "ru": "О XYrminal", "be": "Пра XYrminal", "de": "Über XYrminal",
        "fr": "À propos de XYrminal", "zh": "关于 XYrminal",
        "ja": "XYrminal について", "ko": "XYrminal 정보",
    },
    "Reset to theme": {
        "ru": "Сбросить к теме", "be": "Скінуць да тэмы", "de": "Auf Design zurücksetzen",
        "fr": "Réinitialiser au thème", "zh": "重置为主题色",
        "ja": "テーマに戻す", "ko": "테마로 재설정",
    },
    "Reset all to theme": {
        "ru": "Сбросить всё к теме", "be": "Скінуць усё да тэмы",
        "de": "Alles auf Design zurücksetzen", "fr": "Tout réinitialiser au thème",
        "zh": "全部重置为主题色", "ja": "すべてテーマに戻す", "ko": "모두 테마로 재설정",
    },
    "Show all": {
        "ru": "Показать всё", "be": "Паказаць усё", "de": "Alle anzeigen",
        "fr": "Tout afficher", "zh": "全部显示", "ja": "すべて表示", "ko": "모두 표시",
    },
    "Hide all": {
        "ru": "Скрыть всё", "be": "Схаваць усё", "de": "Alle ausblenden",
        "fr": "Tout masquer", "zh": "全部隐藏", "ja": "すべて非表示",
        "ko": "모두 숨기기",
    },
    "Remember last sent file path": {
        "ru": "Сохранять последний отправленный файл",
        "be": "Захоўваць апошні адпраўлены файл",
        "de": "Zuletzt gesendete Datei merken",
        "fr": "Mémoriser le dernier fichier envoyé",
        "zh": "记住最后发送的文件",
        "ja": "最後に送信したファイルを記憶",
        "ko": "마지막 전송 파일 기억",
    },
    "Saved: {name}": {
        "ru": "Сохранено: {name}", "be": "Захавана: {name}", "de": "Gespeichert: {name}",
        "fr": "Enregistré : {name}", "zh": "已保存：{name}",
        "ja": "保存しました：{name}", "ko": "저장됨: {name}",
    },

    "Connecting": {
        "ru": "Подключение", "be": "Падключэнне", "de": "Verbindung",
        "fr": "Connexion", "zh": "连接", "ja": "接続", "ko": "연결",
    },
    "Setting serial": {
        "ru": "Настройки порта", "be": "Налады порта", "de": "Serielle Einstellungen",
        "fr": "Paramètres série", "zh": "串口设置", "ja": "シリアル設定", "ko": "시리얼 설정",
    },
    "Setting terminal": {
        "ru": "Настройки терминала", "be": "Налады тэрмінала", "de": "Terminal-Einstellungen",
        "fr": "Paramètres du terminal", "zh": "终端设置",
        "ja": "ターミナル設定", "ko": "터미널 설정",
    },
    "Scan": {
        "ru": "Сканировать", "be": "Сканіраваць", "de": "Suchen",
        "fr": "Rechercher", "zh": "扫描", "ja": "スキャン", "ko": "검색",
    },
    "Connect": {
        "ru": "Подключиться", "be": "Падключыцца", "de": "Verbinden",
        "fr": "Connecter", "zh": "连接", "ja": "接続", "ko": "연결",
    },
    "Disconnect": {
        "ru": "Отключиться", "be": "Адключыцца", "de": "Trennen",
        "fr": "Déconnecter", "zh": "断开", "ja": "切断", "ko": "연결 끊기",
    },

    "Baud rate:": {
        "ru": "Скорость:", "be": "Хуткасць:", "de": "Baudrate:",
        "fr": "Débit :", "zh": "波特率：", "ja": "ボーレート：", "ko": "보드레이트:",
    },
    "Data bits:": {
        "ru": "Биты данных:", "be": "Біты дадзеных:", "de": "Datenbits:",
        "fr": "Bits de données :", "zh": "数据位：", "ja": "データビット：", "ko": "데이터 비트:",
    },
    "Stop bits:": {
        "ru": "Стоп-биты:", "be": "Стоп-біты:", "de": "Stoppbits:",
        "fr": "Bits d'arrêt :", "zh": "停止位：", "ja": "ストップビット：", "ko": "정지 비트:",
    },
    "Parity:": {
        "ru": "Чётность:", "be": "Цотнасць:", "de": "Parität:",
        "fr": "Parité :", "zh": "校验位：", "ja": "パリティ：", "ko": "패리티:",
    },
    "Handshaking:": {
        "ru": "Управление потоком:", "be": "Кіраванне патокам:", "de": "Handshake:",
        "fr": "Handshake :", "zh": "流控制：", "ja": "ハンドシェイク：", "ko": "흐름 제어:",
    },
    "Custom…": {
        "ru": "Другое…", "be": "Іншае…", "de": "Benutzerdefiniert…",
        "fr": "Personnalisé…", "zh": "自定义…", "ja": "カスタム…", "ko": "사용자 지정…",
    },

    "Remote host:": {
        "ru": "Удалённый хост:", "be": "Аддалены хост:", "de": "Entfernter Host:",
        "fr": "Hôte distant :", "zh": "远程主机：", "ja": "リモートホスト：", "ko": "원격 호스트:",
    },
    "Remote port:": {
        "ru": "Удалённый порт:", "be": "Аддалены порт:", "de": "Entfernter Port:",
        "fr": "Port distant :", "zh": "远程端口：", "ja": "リモートポート：", "ko": "원격 포트:",
    },
    "Local host:": {
        "ru": "Локальный хост:", "be": "Лакальны хост:", "de": "Lokaler Host:",
        "fr": "Hôte local :", "zh": "本地主机：", "ja": "ローカルホスト：", "ko": "로컬 호스트:",
    },
    "Local port:": {
        "ru": "Локальный порт:", "be": "Лакальны порт:", "de": "Lokaler Port:",
        "fr": "Port local :", "zh": "本地端口：", "ja": "ローカルポート：", "ko": "로컬 포트:",
    },
    "Timeout:": {
        "ru": "Таймаут:", "be": "Тайм-аўт:", "de": "Timeout:",
        "fr": "Délai :", "zh": "超时：", "ja": "タイムアウト：", "ko": "타임아웃:",
    },
    " s": {
        "ru": " с", "be": " с", "de": " s",
        "fr": " s", "zh": " 秒", "ja": " 秒", "ko": " 초",
    },

    "Ping": {
        "ru": "Пинг", "be": "Пінг", "de": "Ping",
        "fr": "Ping", "zh": "Ping", "ja": "Ping", "ko": "Ping",
    },
    "Host:": {
        "ru": "Хост:", "be": "Хост:", "de": "Host:",
        "fr": "Hôte :", "zh": "主机：", "ja": "ホスト：", "ko": "호스트:",
    },
    "Port:": {
        "ru": "Порт:", "be": "Порт:", "de": "Port:",
        "fr": "Port :", "zh": "端口：", "ja": "ポート：", "ko": "포트:",
    },
    "Quantity:": {
        "ru": "Количество:", "be": "Колькасць:", "de": "Anzahl:",
        "fr": "Quantité :", "zh": "数量：", "ja": "回数：", "ko": "횟수:",
    },
    "Period:": {
        "ru": "Период:", "be": "Перыяд:", "de": "Intervall:",
        "fr": "Période :", "zh": "周期：", "ja": "間隔：", "ko": "주기:",
    },
    "Check": {
        "ru": "Проверить", "be": "Праверыць", "de": "Prüfen",
        "fr": "Vérifier", "zh": "检查", "ja": "チェック", "ko": "확인",
    },
    "Start": {
        "ru": "Старт", "be": "Старт", "de": "Start",
        "fr": "Démarrer", "zh": "开始", "ja": "開始", "ko": "시작",
    },
    "Stop": {
        "ru": "Стоп", "be": "Стоп", "de": "Stopp",
        "fr": "Arrêter", "zh": "停止", "ja": "停止", "ko": "정지",
    },

    "AutoScroll": {
        "ru": "Автопрокрутка", "be": "Аўтапрагортка", "de": "Auto-Scroll",
        "fr": "Défilement auto", "zh": "自动滚动", "ja": "自動スクロール", "ko": "자동 스크롤",
    },
    "Timestamps": {
        "ru": "Метки времени", "be": "Меткі часу", "de": "Zeitstempel",
        "fr": "Horodatage", "zh": "时间戳", "ja": "タイムスタンプ", "ko": "타임스탬프",
    },
    "Encoding:": {
        "ru": "Кодировка:", "be": "Кадаванне:", "de": "Kodierung:",
        "fr": "Encodage :", "zh": "编码：", "ja": "エンコーディング：",
        "ko": "인코딩:",
    },
    "Clear": {
        "ru": "Очистить", "be": "Ачысціць", "de": "Leeren",
        "fr": "Effacer", "zh": "清空", "ja": "クリア", "ko": "지우기",
    },

    "Transmit": {
        "ru": "Передача", "be": "Перадача", "de": "Senden",
        "fr": "Émission", "zh": "发送", "ja": "送信", "ko": "전송",
    },
    "Type data and press Enter or Send…": {
        "ru": "Введите данные и нажмите Enter или «Отправить»…",
        "be": "Увядзіце дадзеныя і націсніце Enter або «Адправіць»…",
        "de": "Daten eingeben und Enter oder Senden drücken…",
        "fr": "Saisissez des données et appuyez sur Entrée ou Envoyer…",
        "zh": "输入数据并按 Enter 或发送…",
        "ja": "データを入力し Enter または送信を押してください…",
        "ko": "데이터를 입력하고 Enter 또는 보내기를 누르세요…",
    },
    "Send": {
        "ru": "Отправить", "be": "Адправіць", "de": "Senden",
        "fr": "Envoyer", "zh": "发送", "ja": "送信", "ko": "보내기",
    },
    "+CR": {
        "ru": "+CR", "be": "+CR", "de": "+CR",
        "fr": "+CR", "zh": "+CR", "ja": "+CR", "ko": "+CR",
    },
    "CR=CR+LF": {
        "ru": "CR=CR+LF", "be": "CR=CR+LF", "de": "CR=CR+LF",
        "fr": "CR=CR+LF", "zh": "CR=CR+LF", "ja": "CR=CR+LF", "ko": "CR=CR+LF",
    },

    "Nothing to save.": {
        "ru": "Нечего сохранять.", "be": "Няма чаго захаваць.", "de": "Nichts zu speichern.",
        "fr": "Rien à enregistrer.", "zh": "没有可保存的内容。",
        "ja": "保存する内容がありません。", "ko": "저장할 내용이 없습니다.",
    },
    "Save failed: {err}": {
        "ru": "Ошибка сохранения: {err}", "be": "Памылка захавання: {err}",
        "de": "Speichern fehlgeschlagen: {err}",
        "fr": "Échec de l'enregistrement : {err}",
        "zh": "保存失败：{err}", "ja": "保存に失敗しました：{err}",
        "ko": "저장 실패: {err}",
    },
    "Save log as": {
        "ru": "Сохранить журнал как", "be": "Захаваць журнал як",
        "de": "Protokoll speichern unter", "fr": "Enregistrer le journal sous",
        "zh": "日志另存为", "ja": "ログを名前を付けて保存",
        "ko": "다른 이름으로 로그 저장",
    },
    "XYrminal logs (*.xyrm);;Text files (*.txt);;All files (*)": {
        "ru": "Журналы XYrminal (*.xyrm);;Текстовые файлы (*.txt);;Все файлы (*)",
        "be": "Журналы XYrminal (*.xyrm);;Тэкставыя файлы (*.txt);;Усе файлы (*)",
        "de": "XYrminal-Protokolle (*.xyrm);;Textdateien (*.txt);;Alle Dateien (*)",
        "fr": "Journaux XYrminal (*.xyrm);;Fichiers texte (*.txt);;Tous les fichiers (*)",
        "zh": "XYrminal 日志 (*.xyrm);;文本文件 (*.txt);;所有文件 (*)",
        "ja": "XYrminal ログ (*.xyrm);;テキストファイル (*.txt);;すべてのファイル (*)",
        "ko": "XYrminal 로그 (*.xyrm);;텍스트 파일 (*.txt);;모든 파일 (*)",
    },

    "Pinging {host}:{port} with {count} probes:": {
        "ru": "Обмен пакетами с {host}:{port} ({count} попыток):",
        "be": "Абмен пакетамі з {host}:{port} ({count} спроб):",
        "de": "Ping zu {host}:{port} mit {count} Versuchen:",
        "fr": "Ping vers {host}:{port} avec {count} essais :",
        "zh": "正在对 {host}:{port} 执行 {count} 次探测：",
        "ja": "{host}:{port} に {count} 回 Ping を実行：",
        "ko": "{host}:{port}에 {count}회 핑:",
    },
    "Pinging {host}:{port} periodically:": {
        "ru": "Обмен пакетами с {host}:{port} в периодическом режиме:",
        "be": "Абмен пакетамі з {host}:{port} у перыядычным рэжыме:",
        "de": "Ping zu {host}:{port} im periodischen Modus:",
        "fr": "Ping périodique vers {host}:{port} :",
        "zh": "正在周期性 Ping {host}:{port}：",
        "ja": "{host}:{port} に定期的に Ping：",
        "ko": "{host}:{port}에 주기적으로 핑:",
    },
    "Reply from {host}:{port}: time={ms}ms": {
        "ru": "Ответ от {host}:{port}: время={ms}мс",
        "be": "Адказ ад {host}:{port}: час={ms}мс",
        "de": "Antwort von {host}:{port}: Zeit={ms}ms",
        "fr": "Réponse de {host}:{port} : temps={ms}ms",
        "zh": "来自 {host}:{port} 的回复：时间={ms}ms",
        "ja": "{host}:{port} からの応答：時間={ms}ms",
        "ko": "{host}:{port}에서 응답: 시간={ms}ms",
    },
    "Request timed out.": {
        "ru": "Превышен интервал ожидания для запроса.",
        "be": "Перавышаны інтэрвал чакання запыту.",
        "de": "Zeitüberschreitung der Anforderung.",
        "fr": "Délai d'attente dépassé.",
        "zh": "请求超时。",
        "ja": "要求がタイムアウトしました。",
        "ko": "요청 시간이 초과되었습니다.",
    },
    "Ping statistics for {host}:{port}:": {
        "ru": "Статистика Ping для {host}:{port}:",
        "be": "Статыстыка Ping для {host}:{port}:",
        "de": "Ping-Statistik für {host}:{port}:",
        "fr": "Statistiques Ping pour {host}:{port} :",
        "zh": "{host}:{port} 的 Ping 统计信息：",
        "ja": "{host}:{port} の Ping 統計：",
        "ko": "{host}:{port}의 Ping 통계:",
    },
    "    Packets: Sent = {sent}, Received = {recv}, Lost = {lost}": {
        "ru": "    Пакетов: отправлено = {sent}, получено = {recv}, потеряно = {lost}",
        "be": "    Пакетаў: адпраўлена = {sent}, атрымана = {recv}, страчана = {lost}",
        "de": "    Pakete: Gesendet = {sent}, Empfangen = {recv}, Verloren = {lost}",
        "fr": "    Paquets : Envoyés = {sent}, Reçus = {recv}, Perdus = {lost}",
        "zh": "    数据包：已发送 = {sent}，已接收 = {recv}，丢失 = {lost}",
        "ja": "    パケット：送信 = {sent}、受信 = {recv}、損失 = {lost}",
        "ko": "    패킷: 보냄 = {sent}, 받음 = {recv}, 손실 = {lost}",
    },
    "    ({pct}% loss)": {
        "ru": "    ({pct}% потерь)",
        "be": "    ({pct}% страт)",
        "de": "    ({pct}% Verlust)",
        "fr": "    ({pct}% de perte)",
        "zh": "    （丢失 {pct}%）",
        "ja": "    （損失 {pct}%）",
        "ko": "    ({pct}% 손실)",
    },
    "Approximate round trip times in ms:": {
        "ru": "Приблизительное время приёма-передачи в мс:",
        "be": "Прыблізны час прыёму-перадачы ў мс:",
        "de": "Ungefähre Rundlaufzeiten in ms:",
        "fr": "Temps aller-retour approximatifs en ms :",
        "zh": "往返行程的估计时间（以毫秒为单位）：",
        "ja": "おおよその往復時間（ミリ秒）：",
        "ko": "대략적인 왕복 시간(밀리초):",
    },
    "    Minimum = {mn}ms, Maximum = {mx}ms, Average = {av}ms": {
        "ru": "    Минимальное = {mn}мс, Максимальное = {mx}мс, Среднее = {av}мс",
        "be": "    Мінімальнае = {mn}мс, Максімальнае = {mx}мс, Сярэдняе = {av}мс",
        "de": "    Minimum = {mn}ms, Maximum = {mx}ms, Mittelwert = {av}ms",
        "fr": "    Minimum = {mn}ms, Maximum = {mx}ms, Moyenne = {av}ms",
        "zh": "    最短 = {mn}ms，最长 = {mx}ms，平均 = {av}ms",
        "ja": "    最小 = {mn}ms、最大 = {mx}ms、平均 = {av}ms",
        "ko": "    최소 = {mn}ms, 최대 = {mx}ms, 평균 = {av}ms",
    },

    "[PING:] output": {
        "ru": "Вывод [PING:]", "be": "Вывад [PING:]", "de": "Ausgabe [PING:]",
        "fr": "Sortie [PING:]", "zh": "[PING:] 输出", "ja": "[PING:] 出力", "ko": "[PING:] 출력",
    },
    "[peer] prefix": {
        "ru": "Префикс [peer]", "be": "Прэфікс [peer]",
        "de": "Präfix [peer]", "fr": "Préfixe [peer]",
        "zh": "[peer] 前缀", "ja": "[peer] プレフィックス",
        "ko": "[peer] 접두사",
    },
    "Server events": {
        "ru": "События сервера", "be": "Падзеі сервера",
        "de": "Server-Ereignisse", "fr": "Événements serveur",
        "zh": "服务器事件", "ja": "サーバーイベント", "ko": "서버 이벤트",
    },
    "Transmitted payload": {
        "ru": "Отправленные данные", "be": "Адпраўленыя дадзеныя",
        "de": "Gesendete Nutzdaten",
        "fr": "Données envoyées", "zh": "已发送内容",
        "ja": "送信データ", "ko": "송신 페이로드",
    },
    "Received data": {
        "ru": "Принятые данные", "be": "Прынятыя дадзеныя",
        "de": "Empfangene Daten",
        "fr": "Données reçues", "zh": "接收数据",
        "ja": "受信データ", "ko": "수신 데이터",
    },

    "Purple": {
        "ru": "Фиолетовый", "be": "Фіялетавы", "de": "Violett",
        "fr": "Violet", "zh": "紫色", "ja": "紫", "ko": "보라색",
    },
    "Green": {
        "ru": "Зелёный", "be": "Зялёны", "de": "Grün",
        "fr": "Vert", "zh": "绿色", "ja": "緑", "ko": "녹색",
    },
    "Red": {
        "ru": "Красный", "be": "Чырвоны", "de": "Rot",
        "fr": "Rouge", "zh": "红色", "ja": "赤", "ko": "빨강",
    },
    "Gray": {
        "ru": "Серый", "be": "Шэры", "de": "Grau",
        "fr": "Gris", "zh": "灰色", "ja": "グレー", "ko": "회색",
    },
    "White": {
        "ru": "Белый", "be": "Белы", "de": "Weiß",
        "fr": "Blanc", "zh": "白色", "ja": "白", "ko": "흰색",
    },
    "Black": {
        "ru": "Чёрный", "be": "Чорны", "de": "Schwarz",
        "fr": "Noir", "zh": "黑色", "ja": "黒", "ko": "검정",
    },
    "Beige": {
        "ru": "Бежевый", "be": "Бэжавы", "de": "Beige",
        "fr": "Beige", "zh": "米色", "ja": "ベージュ", "ko": "베이지",
    },
    "Turquoise": {
        "ru": "Бирюзовый", "be": "Бірузовы", "de": "Türkis",
        "fr": "Turquoise", "zh": "青绿色", "ja": "ターコイズ", "ko": "터키옥",
    },
    "Orange": {
        "ru": "Оранжевый", "be": "Аранжавы", "de": "Orange",
        "fr": "Orange", "zh": "橙色", "ja": "オレンジ", "ko": "주황색",
    },
    "Graphite": {
        "ru": "Графитовый", "be": "Графітавы", "de": "Graphit",
        "fr": "Graphite", "zh": "石墨色", "ja": "グラファイト", "ko": "흑연",
    },
    "Sand": {
        "ru": "Песочный", "be": "Пясочны", "de": "Sand",
        "fr": "Sable", "zh": "沙色", "ja": "砂色", "ko": "모래색",
    },
    "Gold": {
        "ru": "Золотой", "be": "Залаты", "de": "Gold",
        "fr": "Or", "zh": "金色", "ja": "金", "ko": "금색",
    },
    "Coral": {
        "ru": "Коралловый", "be": "Каралавы", "de": "Koralle",
        "fr": "Corail", "zh": "珊瑚色", "ja": "コーラル", "ko": "산호색",
    },
    "Mint": {
        "ru": "Мятный", "be": "Мятны", "de": "Minze",
        "fr": "Menthe", "zh": "薄荷色", "ja": "ミント", "ko": "민트",
    },
    "Navy": {
        "ru": "Тёмно-синий", "be": "Цёмна-сіні", "de": "Marineblau",
        "fr": "Bleu marine", "zh": "藏青色", "ja": "ネイビー", "ko": "네이비",
    },
    "Crimson": {
        "ru": "Малиновый", "be": "Малінавы", "de": "Karmesinrot",
        "fr": "Cramoisi", "zh": "深红色", "ja": "クリムゾン", "ko": "크림슨",
    },

    "Turquoise-Orange": {
        "ru": "Бирюзово-оранжевая", "be": "Бірузова-аранжавая", "de": "Türkis-Orange",
        "fr": "Turquoise-Orange", "zh": "青绿-橙色", "ja": "ターコイズ-オレンジ",
        "ko": "터키옥-주황",
    },
    "Graphite-Sand": {
        "ru": "Графитово-песочная", "be": "Графітава-пясочная",
        "de": "Graphit-Sand", "fr": "Graphite-Sable",
        "zh": "石墨-沙色", "ja": "グラファイト-サンド", "ko": "흑연-모래",
    },
    "Purple-Gold": {
        "ru": "Фиолетово-золотая", "be": "Фіялетава-залатая",
        "de": "Violett-Gold", "fr": "Violet-Or",
        "zh": "紫-金色", "ja": "紫-金", "ko": "보라-금색",
    },
    "Coral-Mint": {
        "ru": "Кораллово-мятная", "be": "Каралава-мятная",
        "de": "Koralle-Minze", "fr": "Corail-Menthe",
        "zh": "珊瑚-薄荷", "ja": "コーラル-ミント", "ko": "산호-민트",
    },
    "Navy-Crimson": {
        "ru": "Тёмно-синяя-малиновая", "be": "Цёмна-сіняя-малінавая",
        "de": "Marine-Karmesinrot", "fr": "Marine-Cramoisi",
        "zh": "藏青-深红", "ja": "ネイビー-クリムゾン", "ko": "네이비-크림슨",
    },

    "About {app}": {
        "ru": "О программе {app}", "be": "Пра праграму {app}",
        "de": "Über {app}", "fr": "À propos de {app}",
        "zh": "关于 {app}", "ja": "{app} について", "ko": "{app} 정보",
    },
    "Author: {a}": {
        "ru": "Автор: {a}", "be": "Аўтар: {a}", "de": "Autor: {a}",
        "fr": "Auteur : {a}", "zh": "作者：{a}", "ja": "作者：{a}", "ko": "작성자: {a}",
    },
    "Terminal for COM, TCP, UDP. Client & server, XMODEM/YMODEM, live plot, macros, logging.": {
        "ru": "Терминал для COM, TCP, UDP. Клиент и сервер, XMODEM/YMODEM, графики, макросы, журналирование.",
        "be": "Тэрмінал для COM, TCP, UDP. Кліент і сервер, XMODEM/YMODEM, графікі, макросы, журналіраванне.",
        "de": "Terminal für COM, TCP, UDP. Client & Server, XMODEM/YMODEM, Live-Diagramm, Makros, Protokollierung.",
        "fr": "Terminal pour COM, TCP, UDP. Client et serveur, XMODEM/YMODEM, graphiques, macros, journalisation.",
        "zh": "COM、TCP、UDP 终端。客户端和服务器、XMODEM/YMODEM、实时图表、宏、日志记录。",
        "ja": "COM / TCP / UDP 用ターミナル。クライアント＆サーバー、XMODEM/YMODEM、ライブグラフ、マクロ、ログ。",
        "ko": "COM, TCP, UDP용 터미널. 클라이언트/서버, XMODEM/YMODEM, 실시간 그래프, 매크로, 로깅.",
    },
    "Close": {
        "ru": "Закрыть", "be": "Закрыць", "de": "Schließen",
        "fr": "Fermer", "zh": "关闭", "ja": "閉じる", "ko": "닫기",
    },
    "{app} — Info": {
        "ru": "{app} — информация", "be": "{app} — інфармацыя",
        "de": "{app} — Info", "fr": "{app} — Informations",
        "zh": "{app} — 信息", "ja": "{app} — 情報", "ko": "{app} — 정보",
    },

    "Reset": {
        "ru": "Сброс", "be": "Скід", "de": "Zurücksetzen",
        "fr": "Réinitialiser", "zh": "重置", "ja": "リセット", "ko": "초기화",
    },

    "HEX": {
        "ru": "HEX", "be": "HEX", "de": "HEX",
        "fr": "HEX", "zh": "HEX", "ja": "HEX", "ko": "HEX",
    },
    "DTR": {
        "ru": "DTR", "be": "DTR", "de": "DTR",
        "fr": "DTR", "zh": "DTR", "ja": "DTR", "ko": "DTR",
    },
    "RTS": {
        "ru": "RTS", "be": "RTS", "de": "RTS",
        "fr": "RTS", "zh": "RTS", "ja": "RTS", "ko": "RTS",
    },

    "Configure macros": {
        "ru": "Настроить макросы", "be": "Наладзіць макросы",
        "de": "Makros konfigurieren", "fr": "Configurer les macros",
        "zh": "配置宏", "ja": "マクロを設定", "ko": "매크로 구성",
    },
    "Reset all macros": {
        "ru": "Сбросить все макросы", "be": "Скінуць усе макросы",
        "de": "Alle Makros zurücksetzen", "fr": "Réinitialiser toutes les macros",
        "zh": "重置所有宏", "ja": "すべてのマクロをリセット", "ko": "모든 매크로 초기화",
    },
    "All": {
        "ru": "Все", "be": "Усе", "de": "Alle",
        "fr": "Toutes", "zh": "全部", "ja": "すべて", "ko": "모두",
    },
    "Reset all macros for {label}?": {
        "ru": "Сбросить все макросы для {label}?",
        "be": "Скінуць усе макросы для {label}?",
        "de": "Alle Makros für {label} zurücksetzen?",
        "fr": "Réinitialiser toutes les macros pour {label} ?",
        "zh": "重置 {label} 的所有宏？",
        "ja": "{label} のすべてのマクロをリセットしますか？",
        "ko": "{label}의 모든 매크로를 초기화하시겠습니까?",
    },
    "all tabs": {
        "ru": "все вкладки", "be": "усе ўкладкі", "de": "alle Tabs",
        "fr": "tous les onglets", "zh": "所有标签页",
        "ja": "すべてのタブ", "ko": "모든 탭",
    },
    "Macros — {p}": {
        "ru": "Макросы — {p}", "be": "Макросы — {p}", "de": "Makros — {p}",
        "fr": "Macros — {p}", "zh": "宏 — {p}", "ja": "マクロ — {p}", "ko": "매크로 — {p}",
    },
    "Configure macros for the {p} tab": {
        "ru": "Настройка макросов для вкладки {p}",
        "be": "Налада макросаў для ўкладкі {p}",
        "de": "Makros für den Tab {p} konfigurieren",
        "fr": "Configurer les macros pour l'onglet {p}",
        "zh": "配置 {p} 标签页的宏",
        "ja": "{p} タブのマクロを設定",
        "ko": "{p} 탭의 매크로 구성",
    },
    "Empty — button disabled": {
        "ru": "Пусто — кнопка отключена",
        "be": "Пуста — кнопка адключана",
        "de": "Leer — Schaltfläche deaktiviert",
        "fr": "Vide — bouton désactivé",
        "zh": "空 — 按钮已禁用",
        "ja": "空 — ボタンは無効",
        "ko": "비어 있음 — 버튼 비활성화",
    },
    "HEX (invalid): {t}": {
        "ru": "HEX (неверно): {t}", "be": "HEX (няправільна): {t}",
        "de": "HEX (ungültig): {t}", "fr": "HEX (invalide) : {t}",
        "zh": "HEX（无效）：{t}", "ja": "HEX（無効）：{t}",
        "ko": "HEX (잘못됨): {t}",
    },
    "HEX: {t}": {
        "ru": "HEX: {t}", "be": "HEX: {t}", "de": "HEX: {t}",
        "fr": "HEX : {t}", "zh": "HEX：{t}", "ja": "HEX：{t}", "ko": "HEX: {t}",
    },
    "Text: {t}": {
        "ru": "Текст: {t}", "be": "Тэкст: {t}", "de": "Text: {t}",
        "fr": "Texte : {t}", "zh": "文本：{t}", "ja": "テキスト：{t}", "ko": "텍스트: {t}",
    },
    "Cancel": {
        "ru": "Отмена", "be": "Адмена", "de": "Abbrechen",
        "fr": "Annuler", "zh": "取消", "ja": "キャンセル", "ko": "취소",
    },
    "OK": {
        "ru": "ОК", "be": "ОК", "de": "OK",
        "fr": "OK", "zh": "确定", "ja": "OK", "ko": "확인",
    },

    "Search": {
        "ru": "Поиск", "be": "Пошук", "de": "Suchen",
        "fr": "Rechercher", "zh": "搜索", "ja": "検索", "ko": "검색",
    },
    "Search…": {
        "ru": "Поиск…", "be": "Пошук…", "de": "Suchen…",
        "fr": "Rechercher…", "zh": "搜索…", "ja": "検索…", "ko": "검색…",
    },

    "Plot": {
        "ru": "График", "be": "Графік", "de": "Diagramm",
        "fr": "Graphique", "zh": "图表", "ja": "グラフ", "ko": "그래프",
    },
    "Plot settings": {
        "ru": "Настройки графика", "be": "Налады графіка",
        "de": "Diagramm-Einstellungen", "fr": "Paramètres du graphique",
        "zh": "图表设置", "ja": "グラフ設定", "ko": "그래프 설정",
    },
    "Variable name": {
        "ru": "Имя переменной", "be": "Імя зменнай", "de": "Variablenname",
        "fr": "Nom de variable", "zh": "变量名", "ja": "変数名", "ko": "변수 이름",
    },
    "Parse marker (optional)": {
        "ru": "Маркер парсинга (необязательно)",
        "be": "Маркер парсінгу (неабавязкова)",
        "de": "Parse-Marker (optional)",
        "fr": "Marqueur de parsing (optionnel)",
        "zh": "解析标记（可选）",
        "ja": "パースマーカー（任意）",
        "ko": "파싱 마커 (선택)",
    },
    "+ Add": {
        "ru": "+ Добавить", "be": "+ Дадаць", "de": "+ Hinzufügen",
        "fr": "+ Ajouter", "zh": "+ 添加", "ja": "+ 追加", "ko": "+ 추가",
    },
    "Resume": {
        "ru": "Продолжить", "be": "Працягнуць", "de": "Fortsetzen",
        "fr": "Reprendre", "zh": "继续", "ja": "再開", "ko": "재개",
    },

    "Plot: Start": {
        "ru": "Начать построение", "be": "Пачаць пабудову",
        "de": "Aufzeichnung starten", "fr": "Démarrer la capture",
        "zh": "开始采集", "ja": "キャプチャ開始", "ko": "캡처 시작",
    },
    "Plot: Stop": {
        "ru": "Завершить построение", "be": "Завяршыць пабудову",
        "de": "Aufzeichnung stoppen", "fr": "Arrêter la capture",
        "zh": "停止采集", "ja": "キャプチャ停止", "ko": "캡처 정지",
    },
    "Plot: Pause": {
        "ru": "Пауза построения", "be": "Паўза пабудовы",
        "de": "Aufzeichnung pausieren", "fr": "Mettre en pause",
        "zh": "暂停采集", "ja": "キャプチャ一時停止", "ko": "캡처 일시정지",
    },
    "Plot: Resume": {
        "ru": "Продолжить построение", "be": "Працягнуць пабудову",
        "de": "Aufzeichnung fortsetzen", "fr": "Reprendre la capture",
        "zh": "继续采集", "ja": "キャプチャ再開", "ko": "캡처 재개",
    },

    "Add at least one channel (name required).": {
        "ru": "Добавьте хотя бы один канал (имя обязательно).",
        "be": "Дадайце хаця б адзін канал (імя абавязковае).",
        "de": "Mindestens einen Kanal hinzufügen (Name ist Pflicht).",
        "fr": "Ajoutez au moins un canal (nom obligatoire).",
        "zh": "至少添加一个通道（名称必填）。",
        "ja": "少なくとも 1 つのチャンネルを追加してください（名前は必須）。",
        "ko": "채널을 하나 이상 추가하세요 (이름은 필수).",
    },
    "One row per variable. Name is required; marker is optional (empty marker = take the first number in the incoming chunk). While paused you can edit rows; changes take effect on the next Start.": {
        "ru": "Одна строка на переменную. Имя обязательно; маркер необязателен (пустой маркер = взять первое число из приходящего блока). Во время паузы строки можно редактировать; изменения вступят в силу при следующем запуске.",
        "be": "Адзін радок на зменную. Імя абавязковае; маркер неабавязковы (пусты маркер = узяць першы лік з блока). Падчас паўзы радкі можна рэдагаваць; змены ўступяць у сілу пры наступным запуску.",
        "de": "Eine Zeile pro Variable. Name ist Pflicht; Marker optional (leerer Marker = erste Zahl im eingehenden Block). In der Pause sind Zeilen editierbar; Änderungen greifen beim nächsten Start.",
        "fr": "Une ligne par variable. Nom obligatoire ; marqueur optionnel (marqueur vide = premier nombre du bloc reçu). En pause, les lignes sont éditables ; les changements prennent effet au prochain démarrage.",
        "zh": "每个变量一行。名称必填；标记可选（空标记 = 取接收数据块中的第一个数字）。暂停时可以编辑行；更改将在下次开始时生效。",
        "ja": "変数ごとに 1 行。名前は必須、マーカーは任意（空のマーカー = 受信ブロックの最初の数値を取る）。一時停止中は行を編集できますが、変更は次回の開始時に反映されます。",
        "ko": "변수당 한 행. 이름은 필수, 마커는 선택 (빈 마커 = 수신 블록의 첫 번째 숫자 사용). 일시정지 중에는 행을 편집할 수 있지만 변경은 다음 시작 시 반영됩니다.",
    },

    "Start ping": {
        "ru": "Старт пинга", "be": "Старт пінгу", "de": "Ping starten",
        "fr": "Démarrer le ping", "zh": "开始 ping", "ja": "Ping 開始", "ko": "핑 시작",
    },
    "Stop ping": {
        "ru": "Стоп пинга", "be": "Стоп пінгу", "de": "Ping stoppen",
        "fr": "Arrêter le ping", "zh": "停止 ping", "ja": "Ping 停止", "ko": "핑 정지",
    },

    "Browse…": {
        "ru": "Обзор…", "be": "Агляд…", "de": "Durchsuchen…",
        "fr": "Parcourir…", "zh": "浏览…", "ja": "参照…", "ko": "찾아보기…",
    },
    "Send file": {
        "ru": "Отправить файл", "be": "Адправіць файл", "de": "Datei senden",
        "fr": "Envoyer un fichier", "zh": "发送文件",
        "ja": "ファイルを送信", "ko": "파일 전송",
    },
    "Cancel transfer": {
        "ru": "Отменить передачу", "be": "Адмяніць перадачу",
        "de": "Übertragung abbrechen", "fr": "Annuler le transfert",
        "zh": "取消传输", "ja": "転送をキャンセル", "ko": "전송 취소",
    },
    "No file selected": {
        "ru": "Файл не выбран", "be": "Файл не выбраны",
        "de": "Keine Datei ausgewählt", "fr": "Aucun fichier sélectionné",
        "zh": "未选择文件", "ja": "ファイルが選択されていません",
        "ko": "선택된 파일 없음",
    },
    "Select file to send": {
        "ru": "Выберите файл для отправки",
        "be": "Абярыце файл для адпраўкі",
        "de": "Datei zum Senden auswählen",
        "fr": "Sélectionner un fichier à envoyer",
        "zh": "选择要发送的文件",
        "ja": "送信するファイルを選択",
        "ko": "전송할 파일 선택",
    },
    "Select a file first.": {
        "ru": "Сначала выберите файл.", "be": "Спачатку абярыце файл.",
        "de": "Zuerst eine Datei auswählen.",
        "fr": "Sélectionnez d'abord un fichier.",
        "zh": "请先选择文件。", "ja": "まずファイルを選択してください。",
        "ko": "먼저 파일을 선택하세요.",
    },
    "File not found: {p}": {
        "ru": "Файл не найден: {p}", "be": "Файл не знойдзены: {p}",
        "de": "Datei nicht gefunden: {p}",
        "fr": "Fichier introuvable : {p}",
        "zh": "找不到文件：{p}", "ja": "ファイルが見つかりません：{p}",
        "ko": "파일을 찾을 수 없음: {p}",
    },
    "File is larger than the configured limit ({m} MB).": {
        "ru": "Файл больше установленного лимита ({m} МБ).",
        "be": "Файл больш за ўсталяваны ліміт ({m} МБ).",
        "de": "Datei überschreitet das konfigurierte Limit ({m} MB).",
        "fr": "Le fichier dépasse la limite configurée ({m} Mo).",
        "zh": "文件超过配置的上限（{m} MB）。",
        "ja": "ファイルが設定された上限（{m} MB）を超えています。",
        "ko": "파일이 설정된 한도({m} MB)를 초과합니다.",
    },
    "ZMODEM not implemented yet.": {
        "ru": "ZMODEM пока не реализован.",
        "be": "ZMODEM пакуль не рэалізаваны.",
        "de": "ZMODEM ist noch nicht implementiert.",
        "fr": "ZMODEM pas encore implémenté.",
        "zh": "ZMODEM 尚未实现。",
        "ja": "ZMODEM はまだ実装されていません。",
        "ko": "ZMODEM은 아직 구현되지 않았습니다.",
    },
    "ZMODEM (not implemented)": {
        "ru": "ZMODEM (не реализовано)",
        "be": "ZMODEM (не рэалізавана)",
        "de": "ZMODEM (nicht implementiert)",
        "fr": "ZMODEM (non implémenté)",
        "zh": "ZMODEM（未实现）",
        "ja": "ZMODEM（未実装）",
        "ko": "ZMODEM (미구현)",
    },
    "Raw": {
        "ru": "Байты потока", "be": "Байты патоку", "de": "Rohe Bytes",
        "fr": "Octets bruts", "zh": "原始字节", "ja": "生バイト", "ko": "원시 바이트",
    },
    "XMODEM": {
        "ru": "XMODEM", "be": "XMODEM", "de": "XMODEM",
        "fr": "XMODEM", "zh": "XMODEM", "ja": "XMODEM", "ko": "XMODEM",
    },
    "YMODEM": {
        "ru": "YMODEM", "be": "YMODEM", "de": "YMODEM",
        "fr": "YMODEM", "zh": "YMODEM", "ja": "YMODEM", "ko": "YMODEM",
    },
    "Transfer settings": {
        "ru": "Настройки передачи", "be": "Налады перадачы",
        "de": "Übertragungseinstellungen",
        "fr": "Paramètres de transfert",
        "zh": "传输设置", "ja": "転送設定", "ko": "전송 설정",
    },
    "Chunk size (bytes, raw only):": {
        "ru": "Размер блока (байты, только raw):",
        "be": "Памер блока (байты, толькі raw):",
        "de": "Blockgröße (Bytes, nur raw):",
        "fr": "Taille du bloc (octets, raw uniquement) :",
        "zh": "块大小（字节，仅原始模式）：",
        "ja": "チャンクサイズ（バイト、raw のみ）：",
        "ko": "청크 크기 (바이트, raw 전용):",
    },
    "Chunk delay (ms, raw only):": {
        "ru": "Задержка между блоками (мс, только raw):",
        "be": "Затрымка паміж блокамі (мс, толькі raw):",
        "de": "Blockverzögerung (ms, nur raw):",
        "fr": "Délai entre blocs (ms, raw uniquement) :",
        "zh": "块延迟（毫秒，仅原始模式）：",
        "ja": "チャンク遅延（ms、raw のみ）：",
        "ko": "청크 지연 (ms, raw 전용):",
    },
    "Max file size (MB):": {
        "ru": "Максимальный размер файла (МБ):",
        "be": "Максімальны памер файла (МБ):",
        "de": "Maximale Dateigröße (MB):",
        "fr": "Taille maximale du fichier (Mo) :",
        "zh": "最大文件大小（MB）：",
        "ja": "最大ファイルサイズ（MB）：",
        "ko": "최대 파일 크기 (MB):",
    },
    "Not connected": {
        "ru": "Нет подключения", "be": "Няма падключэння",
        "de": "Nicht verbunden", "fr": "Non connecté",
        "zh": "未连接", "ja": "未接続", "ko": "연결되지 않음",
    },
    "Transfer already running": {
        "ru": "Передача уже идёт", "be": "Перадача ўжо ідзе",
        "de": "Übertragung läuft bereits",
        "fr": "Transfert déjà en cours",
        "zh": "传输已在进行中", "ja": "転送が既に実行中です",
        "ko": "전송이 이미 실행 중입니다",
    },
    "Done": {
        "ru": "Готово", "be": "Гатова", "de": "Fertig",
        "fr": "Terminé", "zh": "完成", "ja": "完了", "ko": "완료",
    },
    "Failed": {
        "ru": "Ошибка", "be": "Памылка", "de": "Fehlgeschlagen",
        "fr": "Échec", "zh": "失败", "ja": "失敗", "ko": "실패",
    },
    "Cancelled": {
        "ru": "Отменено", "be": "Скасавана", "de": "Abgebrochen",
        "fr": "Annulé", "zh": "已取消", "ja": "キャンセル済み", "ko": "취소됨",
    },
    "Waiting for receiver…": {
        "ru": "Ожидание приёмника…", "be": "Чаканне прыёмніка…",
        "de": "Warte auf Empfänger…",
        "fr": "En attente du récepteur…",
        "zh": "等待接收方…", "ja": "受信側を待機中…",
        "ko": "수신 대기 중…",
    },
    "%p% — {a} / {b}": {
        "ru": "%p% — {a} / {b}", "be": "%p% — {a} / {b}", "de": "%p% — {a} / {b}",
        "fr": "%p% — {a} / {b}", "zh": "%p% — {a} / {b}", "ja": "%p% — {a} / {b}",
        "ko": "%p% — {a} / {b}",
    },
    "XMODEM/YMODEM/ZMODEM are not supported over UDP.": {
        "ru": "XMODEM/YMODEM/ZMODEM не поддерживаются по UDP.",
        "be": "XMODEM/YMODEM/ZMODEM не падтрымліваюцца па UDP.",
        "de": "XMODEM/YMODEM/ZMODEM werden über UDP nicht unterstützt.",
        "fr": "XMODEM/YMODEM/ZMODEM ne sont pas pris en charge via UDP.",
        "zh": "UDP 不支持 XMODEM/YMODEM/ZMODEM。",
        "ja": "UDP では XMODEM/YMODEM/ZMODEM はサポートされていません。",
        "ko": "UDP에서는 XMODEM/YMODEM/ZMODEM을 지원하지 않습니다.",
    },

    "TCP Client": {
        "ru": "TCP-клиент", "be": "TCP-кліент", "de": "TCP-Client",
        "fr": "Client TCP", "zh": "TCP 客户端", "ja": "TCP クライアント",
        "ko": "TCP 클라이언트",
    },
    "TCP Server": {
        "ru": "TCP-сервер", "be": "TCP-сервер", "de": "TCP-Server",
        "fr": "Serveur TCP", "zh": "TCP 服务器", "ja": "TCP サーバー",
        "ko": "TCP 서버",
    },
    "UDP Client": {
        "ru": "UDP-клиент", "be": "UDP-кліент", "de": "UDP-Client",
        "fr": "Client UDP", "zh": "UDP 客户端", "ja": "UDP クライアント",
        "ko": "UDP 클라이언트",
    },
    "UDP Server": {
        "ru": "UDP-сервер", "be": "UDP-сервер", "de": "UDP-Server",
        "fr": "Serveur UDP", "zh": "UDP 服务器", "ja": "UDP サーバー",
        "ko": "UDP 서버",
    },

    "Server": {
        "ru": "Сервер", "be": "Сервер", "de": "Server",
        "fr": "Serveur", "zh": "服务器", "ja": "サーバー", "ko": "서버",
    },
    "Listen": {
        "ru": "Слушать", "be": "Слухаць", "de": "Lauschen",
        "fr": "Écouter", "zh": "监听", "ja": "待ち受け", "ko": "수신 대기",
    },
    "Echo": {
        "ru": "Эхо", "be": "Рэха", "de": "Echo",
        "fr": "Écho", "zh": "回显", "ja": "エコー", "ko": "에코",
    },
    "Server echo": {
        "ru": "Эхо сервера", "be": "Рэха сервера", "de": "Server-Echo",
        "fr": "Écho serveur", "zh": "服务器回显",
        "ja": "サーバーエコー", "ko": "서버 에코",
    },
    "Broadcast": {
        "ru": "Broadcast", "be": "Broadcast", "de": "Broadcast",
        "fr": "Diffusion", "zh": "广播", "ja": "ブロードキャスト",
        "ko": "브로드캐스트",
    },
    "Broadcast to all": {
        "ru": "Broadcast всем", "be": "Broadcast усім",
        "de": "Broadcast an alle", "fr": "Diffuser à tous",
        "zh": "广播给所有客户端", "ja": "全員にブロードキャスト",
        "ko": "모두에게 브로드캐스트",
    },
    "Clients:": {
        "ru": "Клиенты:", "be": "Кліенты:", "de": "Clients:",
        "fr": "Clients :", "zh": "客户端：", "ja": "クライアント：",
        "ko": "클라이언트:",
    },
    "Clients: {n}": {
        "ru": "Клиенты: {n}", "be": "Кліенты: {n}", "de": "Clients: {n}",
        "fr": "Clients : {n}", "zh": "客户端：{n}", "ja": "クライアント：{n}",
        "ko": "클라이언트: {n}",
    },
    "Disconnect selected": {
        "ru": "Отключить выбранного", "be": "Адключыць выбранага",
        "de": "Ausgewählten trennen", "fr": "Déconnecter la sélection",
        "zh": "断开所选", "ja": "選択を切断", "ko": "선택 연결 끊기",
    },
    "Disconnect all": {
        "ru": "Отключить всех", "be": "Адключыць усіх",
        "de": "Alle trennen", "fr": "Tout déconnecter",
        "zh": "断开全部", "ja": "すべて切断", "ko": "모두 연결 끊기",
    },
    "Last sender: —": {
        "ru": "Последний отправитель: —", "be": "Апошні адпраўнік: —",
        "de": "Letzter Absender: —", "fr": "Dernier expéditeur : —",
        "zh": "最后发送者：—", "ja": "最後の送信者：—",
        "ko": "마지막 발신자: —",
    },
    "Last sender: {p}": {
        "ru": "Последний отправитель: {p}", "be": "Апошні адпраўнік: {p}",
        "de": "Letzter Absender: {p}", "fr": "Dernier expéditeur : {p}",
        "zh": "最后发送者：{p}", "ja": "最後の送信者：{p}",
        "ko": "마지막 발신자: {p}",
    },
    "File transfer is not available in TCP server mode.": {
        "ru": "Передача файлов недоступна в режиме TCP-сервера.",
        "be": "Перадача файлаў недаступная ў рэжыме TCP-сервера.",
        "de": "Dateiübertragung ist im TCP-Server-Modus nicht verfügbar.",
        "fr": "Le transfert de fichiers n'est pas disponible en mode serveur TCP.",
        "zh": "TCP 服务器模式下不支持文件传输。",
        "ja": "TCP サーバーモードではファイル転送は利用できません。",
        "ko": "TCP 서버 모드에서는 파일 전송을 사용할 수 없습니다.",
    },
    "File transfer is not available in UDP server mode.": {
        "ru": "Передача файлов недоступна в режиме UDP-сервера.",
        "be": "Перадача файлаў недаступная ў рэжыме UDP-сервера.",
        "de": "Dateiübertragung ist im UDP-Server-Modus nicht verfügbar.",
        "fr": "Le transfert de fichiers n'est pas disponible en mode serveur UDP.",
        "zh": "UDP 服务器模式下不支持文件传输。",
        "ja": "UDP サーバーモードではファイル転送は利用できません。",
        "ko": "UDP 서버 모드에서는 파일 전송을 사용할 수 없습니다.",
    },
    "File transfer is not available in this mode.": {
        "ru": "Передача файлов недоступна в этом режиме.",
        "be": "Перадача файлаў недаступная ў гэтым рэжыме.",
        "de": "Dateiübertragung ist in diesem Modus nicht verfügbar.",
        "fr": "Le transfert de fichiers n'est pas disponible dans ce mode.",
        "zh": "此模式下不支持文件传输。",
        "ja": "このモードではファイル転送は利用できません。",
        "ko": "이 모드에서는 파일 전송을 사용할 수 없습니다.",
    },
    
    "Network info": {
        "ru": "Сетевые интерфейсы", "be": "Сетэвыя інтэрфейсы",
        "de": "Netzwerkschnittstellen", "fr": "Interfaces réseau",
        "zh": "网络接口", "ja": "ネットワーク情報", "ko": "네트워크 정보",
    },
    "Hostname:": {
        "ru": "Имя хоста:", "be": "Імя хоста:", "de": "Hostname:",
        "fr": "Nom d'hôte :", "zh": "主机名：", "ja": "ホスト名：", "ko": "호스트 이름:",
    },
    "FQDN:": {
        "ru": "Полное имя:", "be": "Поўнае імя:", "de": "FQDN:",
        "fr": "FQDN :", "zh": "全限定域名：", "ja": "FQDN：", "ko": "FQDN:",
    },
    "Primary IP:": {
        "ru": "Основной IP:", "be": "Асноўны IP:", "de": "Primäre IP:",
        "fr": "IP principale :", "zh": "主 IP：", "ja": "プライマリ IP：", "ko": "기본 IP:",
    },
    "Subnet mask:": {
        "ru": "Маска подсети:", "be": "Маска падсеткі:", "de": "Subnetzmaske:",
        "fr": "Masque de sous-réseau :", "zh": "子网掩码：",
        "ja": "サブネットマスク：", "ko": "서브넷 마스크:",
    },
    "Default gateway:": {
        "ru": "Шлюз по умолчанию:", "be": "Шлюз па змаўчанні:",
        "de": "Standardgateway:", "fr": "Passerelle par défaut :",
        "zh": "默认网关：", "ja": "デフォルトゲートウェイ：", "ko": "기본 게이트웨이:",
    },
    "DNS servers:": {
        "ru": "DNS-серверы:", "be": "DNS-серверы:", "de": "DNS-Server:",
        "fr": "Serveurs DNS :", "zh": "DNS 服务器：",
        "ja": "DNS サーバー：", "ko": "DNS 서버:",
    },
    "Interfaces": {
        "ru": "Интерфейсы", "be": "Інтэрфейсы", "de": "Schnittstellen",
        "fr": "Interfaces", "zh": "接口", "ja": "インターフェース", "ko": "인터페이스",
    },
    "No interfaces found.": {
        "ru": "Интерфейсы не найдены.", "be": "Інтэрфейсы не знойдзены.",
        "de": "Keine Schnittstellen gefunden.", "fr": "Aucune interface trouvée.",
        "zh": "未找到接口。", "ja": "インターフェースが見つかりません。",
        "ko": "인터페이스를 찾을 수 없습니다.",
    },
    "Description:": {
        "ru": "Описание:", "be": "Апісанне:", "de": "Beschreibung:",
        "fr": "Description :", "zh": "描述：", "ja": "説明：", "ko": "설명:",
    },
    "IP:": {
        "ru": "IP:", "be": "IP:", "de": "IP:", "fr": "IP :",
        "zh": "IP：", "ja": "IP：", "ko": "IP:",
    },
    "MASK:": {
        "ru": "Маска:", "be": "Маска:", "de": "MASKE:", "fr": "MASQUE :",
        "zh": "掩码：", "ja": "マスク：", "ko": "마스크:",
    },
    "GW:": {
        "ru": "Шлюз:", "be": "Шлюз:", "de": "GW:", "fr": "Passerelle :",
        "zh": "网关：", "ja": "GW：", "ko": "게이트웨이:",
    },
    "MAC:": {
        "ru": "MAC:", "be": "MAC:", "de": "MAC:", "fr": "MAC :",
        "zh": "MAC：", "ja": "MAC：", "ko": "MAC:",
    },
    "Refresh": {
        "ru": "Обновить", "be": "Абнавіць", "de": "Aktualisieren",
        "fr": "Rafraîchir", "zh": "刷新", "ja": "更新", "ko": "새로 고침",
    },
    "Copy": {
        "ru": "Копировать", "be": "Капіраваць", "de": "Kopieren",
        "fr": "Copier", "zh": "复制", "ja": "コピー", "ko": "복사",
    },
    
    "T-Mode": {
        "ru": "T-Mode", "be": "T-Mode", "de": "T-Mode",
        "fr": "T-Mode", "zh": "T-Mode", "ja": "T-Mode", "ko": "T-Mode",
    },

    "Save format": {
        "ru": "Формат сохранения", "be": "Фармат захавання",
        "de": "Speicherformat", "fr": "Format d'enregistrement",
        "zh": "保存格式", "ja": "保存形式", "ko": "저장 형식",
    },
    "Plain text (.xyrm)": {
        "ru": "Обычный текст (.xyrm)", "be": "Звычайны тэкст (.xyrm)",
        "de": "Klartext (.xyrm)", "fr": "Texte brut (.xyrm)",
        "zh": "纯文本 (.xyrm)", "ja": "プレーンテキスト (.xyrm)", "ko": "일반 텍스트 (.xyrm)",
    },
    "Colored HTML (.xyrmc)": {
        "ru": "Цветной HTML (.xyrmc)", "be": "Каляровы HTML (.xyrmc)",
        "de": "Farbiges HTML (.xyrmc)", "fr": "HTML coloré (.xyrmc)",
        "zh": "彩色 HTML (.xyrmc)", "ja": "カラー HTML (.xyrmc)", "ko": "컬러 HTML (.xyrmc)",
    },
    "XYrminal logs (*.xyrm *.xyrmc);;Plain text (*.xyrm);;Colored HTML (*.xyrmc);;All files (*)": {
        "ru": "Журналы XYrminal (*.xyrm *.xyrmc);;Текст (*.xyrm);;Цветной HTML (*.xyrmc);;Все файлы (*)",
        "be": "Журналы XYrminal (*.xyrm *.xyrmc);;Тэкст (*.xyrm);;Каляровы HTML (*.xyrmc);;Усе файлы (*)",
        "de": "XYrminal-Protokolle (*.xyrm *.xyrmc);;Text (*.xyrm);;Farbiges HTML (*.xyrmc);;Alle Dateien (*)",
        "fr": "Journaux XYrminal (*.xyrm *.xyrmc);;Texte (*.xyrm);;HTML coloré (*.xyrmc);;Tous les fichiers (*)",
        "zh": "XYrminal 日志 (*.xyrm *.xyrmc);;文本 (*.xyrm);;彩色 HTML (*.xyrmc);;所有文件 (*)",
        "ja": "XYrminal ログ (*.xyrm *.xyrmc);;テキスト (*.xyrm);;カラー HTML (*.xyrmc);;すべてのファイル (*)",
        "ko": "XYrminal 로그 (*.xyrm *.xyrmc);;텍스트 (*.xyrm);;컬러 HTML (*.xyrmc);;모든 파일 (*)",
    },

    "Open log…": {
        "ru": "Открыть журнал…", "be": "Адкрыць журнал…",
        "de": "Protokoll öffnen…", "fr": "Ouvrir le journal…",
        "zh": "打开日志…", "ja": "ログを開く…", "ko": "로그 열기…",
    },
    "Open log": {
        "ru": "Открыть журнал", "be": "Адкрыць журнал",
        "de": "Protokoll öffnen", "fr": "Ouvrir le journal",
        "zh": "打开日志", "ja": "ログを開く", "ko": "로그 열기",
    },
    "Opened: {name}": {
        "ru": "Открыт: {name}", "be": "Адкрыты: {name}",
        "de": "Geöffnet: {name}", "fr": "Ouvert : {name}",
        "zh": "已打开：{name}", "ja": "開きました：{name}", "ko": "열림: {name}",
    },
    "Failed to read log: {p}": {
        "ru": "Не удалось прочитать журнал: {p}",
        "be": "Не ўдалося прачытаць журнал: {p}",
        "de": "Protokoll konnte nicht gelesen werden: {p}",
        "fr": "Impossible de lire le journal : {p}",
        "zh": "无法读取日志：{p}",
        "ja": "ログを読み込めませんでした：{p}",
        "ko": "로그를 읽을 수 없습니다: {p}",
    },
    "Failed to open log: {err}": {
        "ru": "Не удалось открыть журнал: {err}",
        "be": "Не ўдалося адкрыць журнал: {err}",
        "de": "Protokoll konnte nicht geöffnet werden: {err}",
        "fr": "Impossible d'ouvrir le journal : {err}",
        "zh": "无法打开日志：{err}",
        "ja": "ログを開けませんでした：{err}",
        "ko": "로그를 열 수 없습니다: {err}",
    },

    "Add scenario…": {
        "ru": "Добавить сценарий…", "be": "Дадаць сцэнар…",
        "de": "Szenario hinzufügen…", "fr": "Ajouter un scénario…",
        "zh": "添加场景…", "ja": "シナリオを追加…", "ko": "시나리오 추가…",
    },
    "Clear scenario": {
        "ru": "Убрать сценарий", "be": "Прыбраць сцэнар",
        "de": "Szenario entfernen", "fr": "Supprimer le scénario",
        "zh": "清除场景", "ja": "シナリオをクリア", "ko": "시나리오 지우기",
    },
    "Select scenario file": {
        "ru": "Выберите файл сценария", "be": "Абярыце файл сцэнара",
        "de": "Szenario-Datei auswählen", "fr": "Sélectionner le fichier de scénario",
        "zh": "选择场景文件", "ja": "シナリオファイルを選択", "ko": "시나리오 파일 선택",
    },
    "XYrminal scenarios (*.xyscen);;All files (*)": {
        "ru": "Сценарии XYrminal (*.xyscen);;Все файлы (*)",
        "be": "Сцэнары XYrminal (*.xyscen);;Усе файлы (*)",
        "de": "XYrminal-Szenarien (*.xyscen);;Alle Dateien (*)",
        "fr": "Scénarios XYrminal (*.xyscen);;Tous les fichiers (*)",
        "zh": "XYrminal 场景 (*.xyscen);;所有文件 (*)",
        "ja": "XYrminal シナリオ (*.xyscen);;すべてのファイル (*)",
        "ko": "XYrminal 시나리오 (*.xyscen);;모든 파일 (*)",
    },
    "Select slot": {
        "ru": "Выбор слота", "be": "Выбар слота",
        "de": "Slot auswählen", "fr": "Sélectionner un slot",
        "zh": "选择槽位", "ja": "スロットを選択", "ko": "슬롯 선택",
    },
    "Which macro slot (1…10) should run this scenario?": {
        "ru": "В какой слот (1…10) поместить сценарий?",
        "be": "У які слот (1…10) змясціць сцэнар?",
        "de": "In welchem Slot (1…10) soll dieses Szenario laufen?",
        "fr": "Dans quel slot (1…10) placer ce scénario ?",
        "zh": "将场景放入哪个槽位（1…10）？",
        "ja": "このシナリオを実行するマクロスロット（1…10）は？",
        "ko": "이 시나리오를 실행할 매크로 슬롯(1…10)은?",
    },
    "Which macro slot (1…10) should be cleared?": {
        "ru": "Какой слот (1…10) очистить?",
        "be": "Які слот (1…10) ачысціць?",
        "de": "Welcher Slot (1…10) soll geleert werden?",
        "fr": "Quel slot (1…10) faut-il vider ?",
        "zh": "清除哪个槽位（1…10）？",
        "ja": "クリアするマクロスロット（1…10）は？",
        "ko": "지울 매크로 슬롯(1…10)은?",
    },
    "Scenario: {p}": {
        "ru": "Сценарий: {p}", "be": "Сцэнар: {p}",
        "de": "Szenario: {p}", "fr": "Scénario : {p}",
        "zh": "场景：{p}", "ja": "シナリオ：{p}", "ko": "시나리오: {p}",
    },
    "[SCENARIO] start: {name} ({count} steps)": {
        "ru": "[SCENARIO] старт: {name} ({count} шагов)",
        "be": "[SCENARIO] старт: {name} ({count} крокаў)",
        "de": "[SCENARIO] Start: {name} ({count} Schritte)",
        "fr": "[SCENARIO] début : {name} ({count} étapes)",
        "zh": "[SCENARIO] 开始：{name}（{count} 步）",
        "ja": "[SCENARIO] 開始：{name}（{count} ステップ）",
        "ko": "[SCENARIO] 시작: {name} ({count} 단계)",
    },
    "[SCENARIO] stopped": {
        "ru": "[SCENARIO] остановлено", "be": "[SCENARIO] спынена",
        "de": "[SCENARIO] gestoppt", "fr": "[SCENARIO] arrêté",
        "zh": "[SCENARIO] 已停止", "ja": "[SCENARIO] 停止しました",
        "ko": "[SCENARIO] 중지됨",
    },
    "[SCENARIO] finished OK": {
        "ru": "[SCENARIO] завершено успешно", "be": "[SCENARIO] завершана паспяхова",
        "de": "[SCENARIO] erfolgreich beendet", "fr": "[SCENARIO] terminé avec succès",
        "zh": "[SCENARIO] 成功完成", "ja": "[SCENARIO] 正常終了",
        "ko": "[SCENARIO] 정상 완료",
    },

    "[SCENARIO] parse error: {err}": {
        "ru": "[SCENARIO] ошибка разбора: {err}",
        "be": "[SCENARIO] памылка разбору: {err}",
        "de": "[SCENARIO] Parser-Fehler: {err}",
        "fr": "[SCENARIO] erreur d'analyse : {err}",
        "zh": "[SCENARIO] 解析错误：{err}",
        "ja": "[SCENARIO] 解析エラー：{err}",
        "ko": "[SCENARIO] 파싱 오류: {err}",
    },
    "[SCENARIO] empty script": {
        "ru": "[SCENARIO] пустой сценарий",
        "be": "[SCENARIO] пусты сцэнар",
        "de": "[SCENARIO] leeres Skript",
        "fr": "[SCENARIO] script vide",
        "zh": "[SCENARIO] 脚本为空",
        "ja": "[SCENARIO] 空のスクリプト",
        "ko": "[SCENARIO] 빈 스크립트",
    },
    "[SCENARIO] start: {name} ({count} steps)": {
        "ru": "[SCENARIO] старт: {name} ({count} шагов)",
        "be": "[SCENARIO] старт: {name} ({count} крокаў)",
        "de": "[SCENARIO] Start: {name} ({count} Schritte)",
        "fr": "[SCENARIO] début : {name} ({count} étapes)",
        "zh": "[SCENARIO] 开始：{name}（{count} 步）",
        "ja": "[SCENARIO] 開始：{name}（{count} ステップ）",
        "ko": "[SCENARIO] 시작: {name} ({count} 단계)",
    },
    "[SCENARIO] stopped": {
        "ru": "[SCENARIO] остановлено", "be": "[SCENARIO] спынена",
        "de": "[SCENARIO] gestoppt", "fr": "[SCENARIO] arrêté",
        "zh": "[SCENARIO] 已停止", "ja": "[SCENARIO] 停止しました",
        "ko": "[SCENARIO] 중지됨",
    },
    "[SCENARIO] finished OK": {
        "ru": "[SCENARIO] завершено успешно",
        "be": "[SCENARIO] завершана паспяхова",
        "de": "[SCENARIO] erfolgreich beendet",
        "fr": "[SCENARIO] terminé avec succès",
        "zh": "[SCENARIO] 成功完成",
        "ja": "[SCENARIO] 正常終了",
        "ko": "[SCENARIO] 정상 완료",
    },
    "[SCENARIO] expect OK: {n}": {
        "ru": "[SCENARIO] expect OK: {n}", "be": "[SCENARIO] expect OK: {n}",
        "de": "[SCENARIO] expect OK: {n}", "fr": "[SCENARIO] expect OK : {n}",
        "zh": "[SCENARIO] expect OK：{n}", "ja": "[SCENARIO] expect OK：{n}",
        "ko": "[SCENARIO] expect OK: {n}",
    },
    "[SCENARIO] step {n}: send {b} byte(s)": {
        "ru": "[SCENARIO] шаг {n}: отправить {b} байт",
        "be": "[SCENARIO] крок {n}: адправіць {b} байт",
        "de": "[SCENARIO] Schritt {n}: {b} Byte senden",
        "fr": "[SCENARIO] étape {n} : envoyer {b} octet(s)",
        "zh": "[SCENARIO] 步骤 {n}：发送 {b} 字节",
        "ja": "[SCENARIO] ステップ {n}：{b} バイト送信",
        "ko": "[SCENARIO] 단계 {n}: {b}바이트 전송",
    },
    "[SCENARIO] step {n}: wait {ms} ms": {
        "ru": "[SCENARIO] шаг {n}: пауза {ms} мс",
        "be": "[SCENARIO] крок {n}: пауза {ms} мс",
        "de": "[SCENARIO] Schritt {n}: {ms} ms warten",
        "fr": "[SCENARIO] étape {n} : attendre {ms} ms",
        "zh": "[SCENARIO] 步骤 {n}：等待 {ms} 毫秒",
        "ja": "[SCENARIO] ステップ {n}：{ms} ms 待機",
        "ko": "[SCENARIO] 단계 {n}: {ms}ms 대기",
    },
    "[SCENARIO] step {n}: expect {needle} ({ms} ms)": {
        "ru": "[SCENARIO] шаг {n}: ждать {needle} ({ms} мс)",
        "be": "[SCENARIO] крок {n}: чакаць {needle} ({ms} мс)",
        "de": "[SCENARIO] Schritt {n}: erwarten {needle} ({ms} ms)",
        "fr": "[SCENARIO] étape {n} : attendre {needle} ({ms} ms)",
        "zh": "[SCENARIO] 步骤 {n}：等待 {needle}（{ms} 毫秒）",
        "ja": "[SCENARIO] ステップ {n}：{needle} を待機（{ms} ms）",
        "ko": "[SCENARIO] 단계 {n}: {needle} 대기 ({ms}ms)",
    },
    "unknown step kind: {k}": {
        "ru": "неизвестный тип шага: {k}", "be": "невядомы тып кроку: {k}",
        "de": "unbekannter Schritt-Typ: {k}",
        "fr": "type d'étape inconnu : {k}",
        "zh": "未知的步骤类型：{k}", "ja": "不明なステップ種別：{k}",
        "ko": "알 수 없는 단계 유형: {k}",
    },
    "[SCENARIO] expect TIMEOUT: {n} (last RX: {r})": {
        "ru": "[SCENARIO] expect TIMEOUT: {n} (последние RX: {r})",
        "be": "[SCENARIO] expect TIMEOUT: {n} (апошнія RX: {r})",
        "de": "[SCENARIO] expect TIMEOUT: {n} (letzte RX: {r})",
        "fr": "[SCENARIO] expect TIMEOUT : {n} (dernier RX : {r})",
        "zh": "[SCENARIO] expect 超时：{n}（最后 RX：{r}）",
        "ja": "[SCENARIO] expect タイムアウト：{n}（最終 RX：{r}）",
        "ko": "[SCENARIO] expect 타임아웃: {n} (마지막 RX: {r})",
    },
    "expect timeout: {n}": {
        "ru": "expect: таймаут {n}", "be": "expect: тайм-аўт {n}",
        "de": "expect: Timeout {n}", "fr": "expect : délai dépassé {n}",
        "zh": "expect 超时：{n}", "ja": "expect タイムアウト：{n}",
        "ko": "expect 타임아웃: {n}",
    },
    "[SCENARIO] FAILED: {err}": {
        "ru": "[SCENARIO] ОШИБКА: {err}", "be": "[SCENARIO] ПАМЫЛКА: {err}",
        "de": "[SCENARIO] FEHLGESCHLAGEN: {err}",
        "fr": "[SCENARIO] ÉCHEC : {err}",
        "zh": "[SCENARIO] 失败：{err}", "ja": "[SCENARIO] 失敗：{err}",
        "ko": "[SCENARIO] 실패: {err}",
    },
    "[SCENARIO] output": {
        "ru": "Вывод [SCENARIO]", "be": "Вывад [SCENARIO]",
        "de": "Ausgabe [SCENARIO]", "fr": "Sortie [SCENARIO]",
        "zh": "[SCENARIO] 输出", "ja": "[SCENARIO] 出力",
        "ko": "[SCENARIO] 출력",
    },
    "[SCENARIO] assert_rx OK: {n}": {
        "ru": "[SCENARIO] assert_rx OK: {n}",
        "be": "[SCENARIO] assert_rx OK: {n}",
        "de": "[SCENARIO] assert_rx OK: {n}",
        "fr": "[SCENARIO] assert_rx OK : {n}",
        "zh": "[SCENARIO] assert_rx 通过：{n}",
        "ja": "[SCENARIO] assert_rx OK：{n}",
        "ko": "[SCENARIO] assert_rx OK: {n}",
    },
    "[SCENARIO] step {n}: send_slow {b} byte(s), {ms} ms/byte": {
        "ru": "[SCENARIO] шаг {n}: send_slow {b} байт, {ms} мс/байт",
        "be": "[SCENARIO] крок {n}: send_slow {b} байт, {ms} мс/байт",
        "de": "[SCENARIO] Schritt {n}: send_slow {b} Byte, {ms} ms/Byte",
        "fr": "[SCENARIO] étape {n} : send_slow {b} octet(s), {ms} ms/octet",
        "zh": "[SCENARIO] 步骤 {n}：send_slow {b} 字节，{ms} ms/字节",
        "ja": "[SCENARIO] ステップ {n}：send_slow {b} バイト、{ms} ms/バイト",
        "ko": "[SCENARIO] 단계 {n}: send_slow {b}바이트, {ms}ms/바이트",
    },
    "[SCENARIO] step {n}: expect_search {needle} ({ms} ms)": {
        "ru": "[SCENARIO] шаг {n}: expect_search {needle} ({ms} мс)",
        "be": "[SCENARIO] крок {n}: expect_search {needle} ({ms} мс)",
        "de": "[SCENARIO] Schritt {n}: expect_search {needle} ({ms} ms)",
        "fr": "[SCENARIO] étape {n} : expect_search {needle} ({ms} ms)",
        "zh": "[SCENARIO] 步骤 {n}：expect_search {needle}（{ms} 毫秒）",
        "ja": "[SCENARIO] ステップ {n}：expect_search {needle}（{ms} ms）",
        "ko": "[SCENARIO] 단계 {n}: expect_search {needle} ({ms}ms)",
    },
    "[SCENARIO] step {n}: assert_rx {needle}": {
        "ru": "[SCENARIO] шаг {n}: assert_rx {needle}",
        "be": "[SCENARIO] крок {n}: assert_rx {needle}",
        "de": "[SCENARIO] Schritt {n}: assert_rx {needle}",
        "fr": "[SCENARIO] étape {n} : assert_rx {needle}",
        "zh": "[SCENARIO] 步骤 {n}：assert_rx {needle}",
        "ja": "[SCENARIO] ステップ {n}：assert_rx {needle}",
        "ko": "[SCENARIO] 단계 {n}: assert_rx {needle}",
    },
    "assert_rx failed: {n}": {
        "ru": "assert_rx не сработал: {n}",
        "be": "assert_rx не спрацаваў: {n}",
        "de": "assert_rx fehlgeschlagen: {n}",
        "fr": "assert_rx a échoué : {n}",
        "zh": "assert_rx 失败：{n}",
        "ja": "assert_rx 失敗：{n}",
        "ko": "assert_rx 실패: {n}",
    },
    "undefined variable: {n}": {
        "ru": "неопределённая переменная: {n}",
        "be": "невызначаная зменная: {n}",
        "de": "undefinierte Variable: {n}",
        "fr": "variable non définie : {n}",
        "zh": "未定义的变量：{n}",
        "ja": "未定義の変数：{n}",
        "ko": "정의되지 않은 변수: {n}",
    },
    "variable interpolation failed": {
        "ru": "ошибка подстановки переменных",
        "be": "памылка падстаноўкі зменных",
        "de": "Variablen-Interpolation fehlgeschlagen",
        "fr": "échec de l'interpolation des variables",
        "zh": "变量插值失败",
        "ja": "変数の埋め込みに失敗しました",
        "ko": "변수 보간 실패",
    },
    
    "CD": {
        "ru": "CD", "be": "CD", "de": "CD", "fr": "CD",
        "zh": "CD", "ja": "CD", "ko": "CD",
    },
    "RI": {
        "ru": "RI", "be": "RI", "de": "RI", "fr": "RI",
        "zh": "RI", "ja": "RI", "ko": "RI",
    },
    "DSR": {
        "ru": "DSR", "be": "DSR", "de": "DSR", "fr": "DSR",
        "zh": "DSR", "ja": "DSR", "ko": "DSR",
    },
    "CTS": {
        "ru": "CTS", "be": "CTS", "de": "CTS", "fr": "CTS",
        "zh": "CTS", "ja": "CTS", "ko": "CTS",
    },

    "Auto-save log": {
        "ru": "Автосохранение", "be": "Аўтазахаванне",
        "de": "Auto-Speichern", "fr": "Enreg. auto",
        "zh": "自动保存", "ja": "自動保存", "ko": "자동 저장",
    },

    "Keep connection": {
        "ru": "Держать соединение", "be": "Трымаць злучэнне",
        "de": "Verbindung halten", "fr": "Maintenir la connexion",
        "zh": "保持连接", "ja": "接続を維持", "ko": "연결 유지",
    },

    "Play": {
        "ru": "Запуск", "be": "Запуск", "de": "Abspielen",
        "fr": "Lire", "zh": "播放", "ja": "再生", "ko": "재생",
    },
    "Pause": {
        "ru": "Пауза", "be": "Паўза", "de": "Pause",
        "fr": "Pause", "zh": "暂停", "ja": "一時停止", "ko": "일시정지",
    },
    "Stop": {
        "ru": "Стоп", "be": "Стоп", "de": "Stopp",
        "fr": "Arrêter", "zh": "停止", "ja": "停止", "ko": "정지",
    },
    "{a} / {b}": {
        "ru": "{a} / {b}", "be": "{a} / {b}", "de": "{a} / {b}",
        "fr": "{a} / {b}", "zh": "{a} / {b}", "ja": "{a} / {b}", "ko": "{a} / {b}",
    },

    "Telegram": {
        "ru": "Telegram", "be": "Telegram", "de": "Telegram",
        "fr": "Telegram", "zh": "Telegram", "ja": "Telegram", "ko": "Telegram",
    },
    "GitHub": {
        "ru": "GitHub", "be": "GitHub", "de": "GitHub",
        "fr": "GitHub", "zh": "GitHub", "ja": "GitHub", "ko": "GitHub",
    },
    "Email": {
        "ru": "Эл. почта", "be": "Эл. пошта", "de": "E-Mail",
        "fr": "E-mail", "zh": "电子邮件", "ja": "メール", "ko": "이메일",
    },

    "Configure triggers": {
        "ru": "Настроить триггеры", "be": "Наладзіць трыгеры",
        "de": "Trigger konfigurieren", "fr": "Configurer les déclencheurs",
        "zh": "配置触发器", "ja": "トリガーを設定", "ko": "트리거 구성",
    },
    "Reset triggers": {
        "ru": "Сбросить триггеры", "be": "Скінуць трыгеры",
        "de": "Trigger zurücksetzen", "fr": "Réinitialiser les déclencheurs",
        "zh": "重置触发器", "ja": "トリガーをリセット", "ko": "트리거 초기화",
    },
    "Reset triggers for {label}?": {
        "ru": "Сбросить триггеры для {label}?",
        "be": "Скінуць трыгеры для {label}?",
        "de": "Trigger für {label} zurücksetzen?",
        "fr": "Réinitialiser les déclencheurs pour {label} ?",
        "zh": "重置 {label} 的触发器？",
        "ja": "{label} のトリガーをリセットしますか？",
        "ko": "{label}의 트리거를 초기화하시겠습니까?",
    },
    "Triggers — {p}": {
        "ru": "Триггеры — {p}", "be": "Трыгеры — {p}",
        "de": "Trigger — {p}", "fr": "Déclencheurs — {p}",
        "zh": "触发器 — {p}", "ja": "トリガー — {p}", "ko": "트리거 — {p}",
    },
    "Text to match (case-insensitive)": {
        "ru": "Текст для поиска (без учёта регистра)",
        "be": "Тэкст для пошуку (без уліку рэгістра)",
        "de": "Text zum Abgleichen (Groß-/Kleinschreibung egal)",
        "fr": "Texte à rechercher (insensible à la casse)",
        "zh": "要匹配的文本（不区分大小写）",
        "ja": "一致させるテキスト（大文字小文字を区別しない）",
        "ko": "일치시킬 텍스트 (대소문자 무시)",
    },
    "Text color": {
        "ru": "Цвет текста", "be": "Колер тэксту",
        "de": "Textfarbe", "fr": "Couleur du texte",
        "zh": "文字颜色", "ja": "文字色", "ko": "텍스트 색상",
    },
    "Background color": {
        "ru": "Цвет фона", "be": "Колер фону",
        "de": "Hintergrundfarbe", "fr": "Couleur de fond",
        "zh": "背景颜色", "ja": "背景色", "ko": "배경색",
    },
    "Each row highlights one substring in the terminal (case-insensitive). If two triggers overlap, the upper one wins. Up to {n} triggers per tab.": {
        "ru": "Каждая строка подсвечивает одну подстроку в терминале (без учёта регистра). При пересечении триггеров выигрывает верхний. До {n} триггеров на вкладку.",
        "be": "Кожны радок падсвечвае адну падстроку ў тэрмінале (без уліку рэгістра). Пры перасячэнні трыгераў перамагае верхні. Да {n} трыгераў на ўкладку.",
        "de": "Jede Zeile hebt einen Teilstring im Terminal hervor (Groß-/Kleinschreibung egal). Bei Überlappung gewinnt der obere Eintrag. Bis zu {n} Trigger pro Tab.",
        "fr": "Chaque ligne met en évidence une sous-chaîne dans le terminal (insensible à la casse). En cas de chevauchement, la ligne supérieure gagne. Jusqu'à {n} déclencheurs par onglet.",
        "zh": "每行在终端中高亮一个子字符串（不区分大小写）。触发器重叠时，靠上的优先。每个标签页最多 {n} 个触发器。",
        "ja": "各行はターミナル内の 1 つの部分文字列を強調表示します（大文字小文字を区別しません）。重なった場合は上の行が優先されます。タブごとに最大 {n} 個。",
        "ko": "각 행은 터미널에서 하나의 부분 문자열을 강조합니다 (대소문자 무시). 겹치는 경우 위쪽 항목이 우선합니다. 탭당 최대 {n}개.",
    },

    "Export CSV": {
        "ru": "Экспорт CSV", "be": "Экспарт CSV", "de": "CSV exportieren",
        "fr": "Exporter CSV", "zh": "导出 CSV", "ja": "CSV エクスポート",
        "ko": "CSV 내보내기",
    },
    "No data to export.": {
        "ru": "Нет данных для экспорта.", "be": "Няма даных для экспарту.",
        "de": "Keine Daten zum Exportieren.", "fr": "Aucune donnée à exporter.",
        "zh": "没有可导出的数据。", "ja": "エクスポートするデータがありません。",
        "ko": "내보낼 데이터가 없습니다.",
    },
    "Export plot data": {
        "ru": "Экспорт данных графика", "be": "Экспарт даных графіка",
        "de": "Diagrammdaten exportieren",
        "fr": "Exporter les données du graphique",
        "zh": "导出图表数据", "ja": "グラフデータをエクスポート",
        "ko": "그래프 데이터 내보내기",
    },
    "CSV files (*.csv);;All files (*)": {
        "ru": "Файлы CSV (*.csv);;Все файлы (*)",
        "be": "Файлы CSV (*.csv);;Усе файлы (*)",
        "de": "CSV-Dateien (*.csv);;Alle Dateien (*)",
        "fr": "Fichiers CSV (*.csv);;Tous les fichiers (*)",
        "zh": "CSV 文件 (*.csv);;所有文件 (*)",
        "ja": "CSV ファイル (*.csv);;すべてのファイル (*)",
        "ko": "CSV 파일 (*.csv);;모든 파일 (*)",
    },
    "Export failed: {err}": {
        "ru": "Ошибка экспорта: {err}", "be": "Памылка экспарту: {err}",
        "de": "Export fehlgeschlagen: {err}",
        "fr": "Échec de l'exportation : {err}",
        "zh": "导出失败：{err}", "ja": "エクスポートに失敗しました：{err}",
        "ko": "내보내기 실패: {err}",
    },
    "Exported: {name}": {
        "ru": "Экспортировано: {name}", "be": "Экспартавана: {name}",
        "de": "Exportiert: {name}", "fr": "Exporté : {name}",
        "zh": "已导出：{name}", "ja": "エクスポートしました：{name}",
        "ko": "내보냄: {name}",
    },

    "System": {
        "ru": "Системная", "be": "Сістэмная", "de": "System",
        "fr": "Système", "zh": "系统", "ja": "システム", "ko": "시스템",
    },

    "UI scale": {
        "ru": "Масштаб системы", "be": "Маштаб сістэмы",
        "de": "UI-Skalierung", "fr": "Échelle de l'interface",
        "zh": "界面缩放", "ja": "UI スケール", "ko": "UI 크기",
    },

    "Custom…": {
        "ru": "Пользовательская…", "be": "Карыстальніцкая…",
        "de": "Benutzerdefiniert…", "fr": "Personnalisé…",
        "zh": "自定义…", "ja": "カスタム…", "ko": "사용자 지정…",
    },
    "Custom theme": {
        "ru": "Пользовательская тема", "be": "Карыстальніцкая тэма",
        "de": "Benutzerdefiniertes Design", "fr": "Thème personnalisé",
        "zh": "自定义主题", "ja": "カスタムテーマ", "ko": "사용자 지정 테마",
    },
    "Pick any color for each part of the interface. Saving switches to the custom theme immediately.": {
        "ru": "Выберите любой цвет для каждой части интерфейса. После сохранения тема применяется сразу.",
        "be": "Выберыце любы колер для кожнай часткі інтэрфейсу. Пасля захавання тэма ўжываецца адразу.",
        "de": "Wählen Sie eine beliebige Farbe für jeden Teil der Oberfläche. Nach dem Speichern wird das Design sofort angewendet.",
        "fr": "Choisissez une couleur pour chaque partie de l'interface. Après enregistrement, le thème est appliqué immédiatement.",
        "zh": "为界面的每个部分选择任意颜色。保存后立即应用。",
        "ja": "インターフェースの各部分の色を自由に選べます。保存するとすぐに適用されます。",
        "ko": "인터페이스의 각 부분에 원하는 색상을 선택하세요. 저장하면 즉시 적용됩니다.",
    },
    "Reset to defaults": {
        "ru": "Сбросить к значениям по умолчанию",
        "be": "Скінуць да значэнняў па змаўчанні",
        "de": "Auf Standardwerte zurücksetzen",
        "fr": "Réinitialiser aux valeurs par défaut",
        "zh": "重置为默认值", "ja": "既定値にリセット",
        "ko": "기본값으로 재설정",
    },
    "Apply": {
        "ru": "Применить", "be": "Ужыць", "de": "Anwenden",
        "fr": "Appliquer", "zh": "应用", "ja": "適用", "ko": "적용",
    },

    "Random": {
        "ru": "Случайная", "be": "Выпадковая", "de": "Zufällig",
        "fr": "Aléatoire", "zh": "随机", "ja": "ランダム", "ko": "랜덤",
    },
}


def translate_tree(root: ET.Element, lang: str) -> int:
    count = 0
    for context in root.findall("context"):
        for message in context.findall("message"):
            src_el = message.find("source")
            tr_el  = message.find("translation")
            if src_el is None or tr_el is None:
                continue
            src = src_el.text or ""

            tr_text = T.get(src, {}).get(lang)
            if tr_text is not None:
                tr_el.text = tr_text
                if "type" in tr_el.attrib:
                    del tr_el.attrib["type"]
                count += 1
    return count


def main() -> None:
    if not TEMPLATE.exists():
        print(f"ERROR: template not found: {TEMPLATE}")
        print("Run pylupdate6 first to generate it.")
        return

    print(f"Template: {TEMPLATE.name}")

    for lang in LANGS:
        tree = ET.parse(TEMPLATE)
        root = tree.getroot()

        n = translate_tree(root, lang)

        out_path = I18N_DIR / f"xyrminal_{lang}.ts"
        body = ET.tostring(root, encoding="unicode")
        with out_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<!DOCTYPE TS>\n')
            f.write(body)
            f.write("\n")

        print(f"  {out_path.name}: {n} translations written")

    print("\nDone. Now compile with:")
    for lang in LANGS:
        print(f"  pyside6-lrelease i18n/xyrminal_{lang}.ts -qm i18n/xyrminal_{lang}.qm")


if __name__ == "__main__":
    main()