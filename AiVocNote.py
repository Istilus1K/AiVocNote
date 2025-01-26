import csv
import os
import logging
import google.generativeai as genai
import pandas as pd
import subprocess

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def fetch_word_data(language, word):
    """AIに単語データをリクエストし、結果を返す関数"""
    try:
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

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logging.error("Environment variable 'GEMINI_API_KEY' is not set.")
            return
        genai.configure(api_key=gemini_api_key)
        gemini_pro = genai.GenerativeModel("gemini-pro")

        response = gemini_pro.generate_content(prompt)
        result = response.text.strip()

        if result:
            logging.info(f"Generated result:\n{result}")

            result_lines = result.split('\n')
            while len(result_lines) < 9:
                result_lines.append('')

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
            logging.error("No results found.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

def save_to_csv(row):
    """辞書形式のデータをCSVに保存する"""
    import csv
    filename = "words.csv"
    fieldnames = ["word", "pronunciation", "meaning", "example1", "example1_translation", 
                "example2", "example2_translation", "example3", "example3_translation"]

    try:
        with open(filename, mode='a', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if file.tell() == 0:
                writer.writeheader()

            writer.writerow(row)

        logging.info(f"Data saved to CSV file: {filename}")

    except Exception as e:
        logging.error(f"An error occurred while saving to CSV: {e}")



def generate_vocabulary_pdf(tex_file_path, csv_file_path, section_num, output_directory):
    """
    単語ノートのPDFを生成する関数。

    Args:
        tex_file_path (str): TeXテンプレートのファイルパス。
        csv_file_path (str): 語彙データのCSVファイルパス。
        section_num (int): セクション番号。
        output_directory (str): PDF出力先のディレクトリパス。
    """
    def insert_text_above_flag(tex_file_path, flag, new_text):
        with open(tex_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            if flag in line:
                lines.insert(i, new_text + '\n\n')
                break

        with open(tex_file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

    data = pd.read_csv(csv_file_path)

    if data.empty:
        print("No data in the CSV file. Stopping process.")
        return

    last_row = data.iloc[-1]
    word_entry = r"""
\entry{""" + str(last_row['word']) + r"""}{[\ipa{""" + str(last_row['pronunciation']) + r"""}]}{""" + str(last_row['meaning']) + r"""}{\webreibun\par """ + str(last_row['example1']) + r" \par " + str(last_row['example1_translation']) + r""" \par """ + str(last_row['example2']) + r" \par " + str(last_row['example2_translation']) + r""" \par """ + str(last_row['example3']) + r" \par " + str(last_row['example3_translation']) + r""" \par }
"""

    tex_memo = '{\\reibun\par '

    while True:
        user_input = input("Enter a text or section number(1~3) (or 'n' to reset): ")

        try:
            section_num = int(user_input)
            if 1 <= section_num <= 3:
                tex_memo = tex_memo + '}'

                word_entry += tex_memo

                section_flag = f"%section{section_num}"

                insert_text_above_flag(tex_file_path, section_flag, word_entry)

                try:
                    subprocess.run(['xelatex', '-output-directory', output_directory, tex_file_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error during PDF compilation: {e}")
                    return

                temp_files = [
                    'vocabulary_note.aux', 'vocabulary_note.log', 
                    'vocabulary_note.ind', 'vocabulary_note.ilg', 
                    'vocabulary_note.idx'
                ]
                for temp_file in temp_files:
                    subprocess.run(['rm', f'{output_directory}/{temp_file}'])

                print("PDF successfully generated.")
                break
            else:
                print("Please enter a section number between 1 and 3.")
        except ValueError:
            if user_input.lower() == 'n':
                tex_memo = ''

                print("Program will exit.")
                break
            else:
                tex_memo = tex_memo + user_input + '\par '  # テキストを追加


def main():
    #####################################################################
    # 言語を設定
    language = 'インドネシア語'

    # pdfの保存先を設定
    output_directory = os.getcwd()
    #####################################################################

    word = input("Enter a word!: ")

    section_num = 1

    if word:
        fetch_word_data(language, word)

        generate_vocabulary_pdf(
            tex_file_path='vocabulary_note.tex',
            csv_file_path='words.csv',
            section_num=section_num,
            output_directory=output_directory
        )

if __name__ == "__main__":
    main()