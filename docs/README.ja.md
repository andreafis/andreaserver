# AndreaServer

**小さなホームサーバー。** AndreaServer は、DietPi を入れたミニ PC をコマンドひとつで本格的なホームサーバーに変えます。

[🇮🇹 Italiano](README.it.md) · [🇬🇧 English](../README.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · 🇯🇵 日本語

## インストールされるもの

| 名前 | 役割 | 場所 |
|---|---|---|
| Pi-hole | ネットワーク全体の広告をブロック | `http://IP/admin` |
| Jellyfin | 映画や音楽をテレビ・スマホ・ブラウザーで再生 | `http://IP:8096` |
| Samba | ネットワーク共有フォルダー | `\\IP\Media` |
| WireGuard / OpenVPN | 外出先から自宅に接続 | `dietpi-software` |
| ウェブコンソール | サーバーの状態、グラフ、操作ボタン | `http://IP:8088` |
| バナー | ログインのたびにサーバーの概要を表示 | ログイン時 |
| テキスト Shell | ターミナル上のウィンドウ、メニュー、マウス操作 | コマンド `D` |

ショートカット: `A` バナー · `D` Shell · `M` モニター · `K` Jellyfin 停止 · `k` Jellyfin 再起動 · `R` 再起動 · `backup-server` 設定のバックアップ。

## インストール

1. ミニ PC に [DietPi](https://dietpi.com)（Debian）をインストールし、初回起動を完了します。
2. 外付けディスクを接続し、`dietpi-drive_manager` でマウントします。
3. root で実行します。

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/andreafis/andreaserver/main/bootstrap.sh) --lang ja
```

セットアップでは、言語、ディスク、天気を表示する都市、共有フォルダー名、パスワードを尋ねます。ソフトウェアのインストール中に DietPi からいくつか質問されることがあります（VPN の設定など）。

質問なしで実行する場合: `andreaserver.conf.example` をコピーして記入し、`./install.sh --config my.conf` を実行します。

## 含まれていないもの

このリポジトリには、鍵、パスワード、トークン、自宅のアドレス、個人データは一切含まれていません。VPN の鍵、パスワード、証明書はマシンごとに新しく作成されます。ローカル設定は `/etc/andreaserver/andreaserver.conf` にあり、公開してはいけません。公開の前には必ず `tools/check-secrets.sh` を実行してください。

## 知っておくこと

- DietPi 10（Debian 12）の x86_64 サーバーをもとに作成しました。インストーラーはまだ新規のマシンでは試していません。DietPi が必須で、素の Debian ではインストーラーは停止します。
- 共有フォルダーはパスワードなしで開けるようにできます（セットアップ時に選択）。信頼できる家庭内ネットワークでのみ使ってください。
- バナー、ウェブコンソール、Shell は今のところイタリア語のみです。インストーラーとドキュメントは 5 言語に対応しています。
- 日本語の画面は SSH 接続のターミナルで表示してください。本体に直接つないだ画面では文字化けします。
- `git pull` のあとに AndreaServer のファイルを更新するには: `/opt/andreaserver/install.sh --files-only`

## ライセンス

[MIT](../LICENSE)
