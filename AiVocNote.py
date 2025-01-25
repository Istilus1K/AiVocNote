import csv
import os
import logging
import google.generativeai as genai
import pandas as pd
import subprocess

# ログ設定（INFOレベルを有効化）
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def save_to_csv(data, filename="words.csv"):
    """データをCSVファイルに保存する関数"""
    try:
        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(data)
    except Exception as e:
        logging.error(f"CSVへの書き込みに失敗しました: {e}")

def fetch_word_data(language, word):
    """AIに単語データをリクエストし、結果を返す関数"""
    try:
        # プロンプトを作成
        prompt = (f"{language}の{word}という単語を辞書的に解説してください。\n\n"
                "以下の情報を、必ずカンマ区切りの形式で返してください（例: word, pronunciation, meaning, example1, Japanese translation1, example2, Japanese translation2, example3, Japanese translation3）：\n"
                "1. 単語 (word),\n"
                "2. 発音 (pronunciation),\n"
                "3. 意味 (meaning),\n"
                "4. 例文1 (example1),\n"
                "5. 日本語訳1 (Japanese translation1),\n"
                "6. 例文2 (example2),\n"
                "7. 日本語訳2 (Japanese translation2),\n"
                "8. 例文3 (example3),\n"
                "9. 日本語訳3 (Japanese translation3),\n\n"
                "もし情報が見つからない場合や不完全な場合は、次のように回答してください：\n"
                "- 結果が見つかりませんでした。\n"
                "- 情報が不足しています（カンマ区切りの形式で返す）"
                "(例：hati,/ˈɑːti/,心,Hati saya senang,私の心は喜んでいる,Dia adalah orang yang baik hati,彼/彼女は心優しい人です,Hati-hati!,気を付けて!)\n"
                "カンマを忘れないこと、必ず9つの項目を返すことに注意して下さい。\n")


        # APIリクエスト（gemini_proの生成メソッドを呼び出し）
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logging.error("環境変数 'GEMINI_API_KEY' が設定されていません。")
            return
        genai.configure(api_key=gemini_api_key)
        gemini_pro = genai.GenerativeModel("gemini-pro")

        response = gemini_pro.generate_content(prompt)
        result = response.text.strip()  # 不要な空白を削除

        # 結果があればCSVに保存
        if result:
            logging.info(f"生成された結果: {result}")
            save_to_csv(result.split(","))
        else:
            logging.error(f"結果が見つかりませんでした。")

    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")


def generate_vocabulary_pdf(tex_file_path, csv_file_path, section_num, output_directory):
    """
    単語ノートのPDFを生成する関数。

    Args:
        tex_file_path (str): TeXテンプレートのファイルパス。
        csv_file_path (str): 語彙データのCSVファイルパス。
        section_num (int): セクション番号。
        output_directory (str): PDF出力先のディレクトリパス。
    """
    # TeXファイルにテキストを挿入する関数
    def insert_text_above_flag(tex_file_path, flag, new_text):
        with open(tex_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            if flag in line:
                lines.insert(i, new_text + '\n\n')
                break

        with open(tex_file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

    # CSVファイルからデータを読み込む
    data = pd.read_csv(csv_file_path)

    # CSVが空でないかチェック
    if data.empty:
        print("CSVファイルにデータがありません。処理を中止します。")
        return

    # 単語データをTeXフォーマットに変換
    word_entries = ""
    for _, row in data.iterrows():
        word_entry = r"""
\entry{""" + str(row['word']) + r"""}{[\ipa{""" + str(row['pronunciation']) + r"""}]}{""" + str(row['meaning']) + r"""}{\webreibun\par """ + str(row['example1']) + r" \par " + str(row['example1_translation']) + r""" \par """ + str(row['example2']) + r" \par " + str(row['example2_translation']) + r""" \par """ + str(row['example3']) + r" \par " + str(row['example3_translation']) + r""" \par }
"""
        word_entries += word_entry

    # 入力部分
    tex_memo = '{\\reibun\par '

    # セクション番号とテキストを同時に処理
    while True:
        user_input = input("Enter a text or section number(1~3) (or 'n' to reset): ")

        try:
            section_num = int(user_input)  # セクション番号が入力された場合
            if 1 <= section_num <= 3:  # セクション番号が1~3の範囲か確認
                tex_memo = tex_memo + '}'

                                # テキストを追加する処理（ここではtex_memoの内容を使う）
                word_entries += tex_memo  # この行を追加

                # セクション番号に合わせて追加
                section_flag = f"%section{section_num}"

                # TeXファイルに追加する内容を挿入
                insert_text_above_flag(tex_file_path, section_flag, word_entries)

                # TeXをPDFにコンパイル
                try:
                    subprocess.run(['xelatex', '-output-directory', output_directory, tex_file_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error during PDF compilation: {e}")
                    return

                # 不要なファイルの削除
                temp_files = [
                    'vocabulary_note.aux', 'vocabulary_note.log', 
                    'vocabulary_note.ind', 'vocabulary_note.lig', 
                    'vocabulary_note.idx'
                ]
                for temp_file in temp_files:
                    subprocess.run(['rm', f'{output_directory}/{temp_file}'])

                # CSV内容の削除
                data = data.iloc[0:0]  # CSVの内容を削除
                data.to_csv(csv_file_path, index=False)

                print("PDFが正常に生成されました。CSVの内容も削除されました。")

                break  # セクション番号が入力されるとループを終了
            else:
                print("セクション番号は1~3の範囲で入力してください。")
        except ValueError:
            if user_input.lower() == 'n':  # 'n' が入力された場合はリセット
                tex_memo = ''

                # CSV内容の削除
                data = data.iloc[0:0]  # CSVの内容を削除
                data.to_csv(csv_file_path, index=False)  # 空のデータを保存

                print("CSVの内容が削除されました。プログラムを終了します。")
                break  # プログラムを終了
            else:
                tex_memo = tex_memo + user_input + '\par '  # テキストを追加




def main():
    #####################################################################
    # 言語を設定
    language = 'インドネシア語'

    # pdfの保存先を設定
    output_directory = os.getcwd()
    #####################################################################

    # 標準入力で単語を受け取る
    word = input("Enter a word!: ")

    # 初期セクション番号を指定
    section_num = 1  # 初期セクション番号

    # fetch_word_data を実行して単語データを取得
    if word:
        fetch_word_data(language, word)  # fetch_word_dataの実行を先に行う

        # generate_vocabulary_pdf を呼び出して PDF を生成
        generate_vocabulary_pdf(
            tex_file_path='vocabulary_note.tex',
            csv_file_path='words.csv',
            section_num=section_num,  # セクション番号を設定
            output_directory=output_directory
        )

if __name__ == "__main__":
    main()