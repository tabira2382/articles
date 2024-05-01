# Pythonイメージをベースにする
FROM python:3.9

# 作業ディレクトリを設定
WORKDIR /articles

# 依存関係ファイルをコピー
COPY requirements.txt /articles/

# 依存関係をインストール
RUN pip install -r requirements.txt

# プロジェクトファイルをコピー
COPY . /articles/
