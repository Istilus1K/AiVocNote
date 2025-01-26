import csv
import os
import logging
import google.generativeai as genai
import pandas as pd
import subprocess

# ログ設定（INFOレベルを有効化）
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def fetch_word_data(language, word):
    """AIに単語データをリクエストし、結果を返す関数"""
    try:
        # プロンプトを作成
        prompt = (f"{language}の{word}という単語を辞書的に解説してください。\n"
                "以下の9つ情報を、それぞれ改行して返してください:\n"
                "単語 (word),\n"
                "発音 (pronunciation),\n"
                "意味 (meaning),\n"
                "例文1 (example1),\n"
                "日本語訳1 (example1_translation),\n"
                "例文2 (example2),\n"
                "日本語訳2 (example2_translation),\n"
                "例文3 (example3),\n"
                "日本語訳3 (example3_translation)。\n\n"
                "もし情報が見つからない場合や不完全な場合は、次のように回答してください：\n"
                "- 結果が見つかりませんでした。\n"
                "- 情報が不足しています（9行で返してください）。\n\n"
                "例 (インドネシア語のhatiという単語):\n"
                "hati\n"
                "/ˈɑːti/\n"
                "心\n"
                "Hati saya senang\n"
                "私の心は喜んでいる\n"
                "Dia adalah orang yang baik hati\n"
                "彼/彼女は心優しい人です\n"
                "Hati-hati!\n"
                "気を付けて!\n")

        # APIリクエスト
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logging.error("環境変数 'GEMINI_API_KEY' が設定されていません。")
            return
        genai.configure(api_key=gemini_api_key)
        gemini_pro = genai.GenerativeModel("gemini-pro")

        response = gemini_pro.generate_content(prompt)
        result = response.text.strip()  # 不要な空白を削除

        # 結果があれば処理
        if result:
            logging.info(f"生成された結果:\n{result}")

            # 改行で分割し、9項目に満たない場合は空欄で埋める
            result_lines = result.split('\n')
            while len(result_lines) < 9:
                result_lines.append('')

            # CSV保存形式に変換
            csv_row = {
                "word": result_lines[0],
                "pronunciation": result_lines[1],
                "meaning": result_lines[2],
                "example1": result_lines[3],
                "example1_translation": result_lines[4],
                "example2": result_lines[5],
                "example2_translation": result_lines[6],
                "example3": result_lines[7],
                "example3_translation": result_lines[8],
            }

            save_to_csv(csv_row)
        else:
            logging.error("結果が見つかりませんでした。")

    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

def save_to_csv(row):
    """辞書形式のデータをCSVに保存する"""
    import csv
    filename = "words.csv"
    fieldnames = ["word", "pronunciation", "meaning", "example1", "example1_translation", 
                "example2", "example2_translation", "example3", "example3_translation"]

    # CSVにデータを書き込む
    try:
        with open(filename, mode='a', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # ファイルが空の場合ヘッダーを書き込む
            if file.tell() == 0:
                writer.writeheader()

            writer.writerow(row)

        logging.info(f"データをCSVファイルに保存しました: {filename}")

    except Exception as e:
        logging.error(f"CSV保存中にエラーが発生しました: {e}")



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

    # 最終行のデータをTeXフォーマットに変換
    last_row = data.iloc[-1]
    word_entry = r"""
\entry{""" + str(last_row['word']) + r"""}{[\ipa{""" + str(last_row['pronunciation']) + r"""}]}{""" + str(last_row['meaning']) + r"""}{\webreibun\par """ + str(last_row['example1']) + r" \par " + str(last_row['example1_translation']) + r""" \par """ + str(last_row['example2']) + r" \par " + str(last_row['example2_translation']) + r""" \par """ + str(last_row['example3']) + r" \par " + str(last_row['example3_translation']) + r""" \par }
"""
    
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
                word_entry += tex_memo  # この行を追加

                # セクション番号に合わせて追加
                section_flag = f"%section{section_num}"

                # TeXファイルに追加する内容を挿入
                insert_text_above_flag(tex_file_path, section_flag, word_entry)

                # TeXをPDFにコンパイル
                try:
                    subprocess.run(['xelatex', '-output-directory', output_directory, tex_file_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error during PDF compilation: {e}")
                    return

                # 不要なファイルの削除
                temp_files = [
                    'vocabulary_note.aux', 'vocabulary_note.log', 
                    'vocabulary_note.ind', 'vocabulary_note.ilg', 
                    'vocabulary_note.idx'
                ]
                for temp_file in temp_files:
                    subprocess.run(['rm', f'{output_directory}/{temp_file}'])

                print("PDFが正常に生成されました。")
                break  # セクション番号が入力されるとループを終了
            else:
                print("セクション番号は1~3の範囲で入力してください。")
        except ValueError:
            if user_input.lower() == 'n':  # 'n' が入力された場合はリセット
                tex_memo = ''

                print("プログラムを終了します。")
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