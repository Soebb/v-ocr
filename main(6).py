import requests
import numpy as np
import os, datetime, subprocess, shutil, json, math, time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if "BOT_TOKEN" in os.environ:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    API_ID = os.environ.get("API_ID")
    API_HASH = os.environ.get("API_HASH")
else:
    BOT_TOKEN = " "
    API_ID = " "
    API_HASH = " "

Bot = Client(
    "Bot",
    bot_token = BOT_TOKEN,
    api_id = API_ID,
    api_hash = API_HASH
)

START_TXT = """
Hi {}
I am subtitle extractor Bot.
> `I can extract hard-coded subtitle from videos.`
Send me a video to get started.
"""

START_BTN = InlineKeyboardMarkup(
        [[
        InlineKeyboardButton("Source Code", url="https://github.com/samadii/VidSubExtract-Bot"),
        ]]
    )


@Bot.on_message(filters.command(["start"]))
async def start(bot, update):
    text = START_TXT.format(update.from_user.mention)
    reply_markup = START_BTN
    await update.reply_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

@Bot.on_message(filters.command(["cancel"]))
async def cancel_progress(_, m):
    try:
        shutil.rmtree("temp/")
    except:
        await m.reply("can't cancel. maybe there wasn't any progress in process.")
    else:
        await m.reply("canceled successfully.")


#language
LANG="fas"

@Bot.on_message(filters.private & (filters.video | filters.document))
async def main(bot, m):
    ms = await m.reply("downloading")
    try:
        shutil.rmtree("temp/")
    except:
        pass
    time.sleep(2)
    try:
        os.makedirs("temp/")
    except:
        pass
    media = m.video or m.document
    await m.download("temp/vid.mp4")
    await ms.edit("`Now Extracting..`\n\n for cancel progress, send /cancel", parse_mode='md')
    if m.video:
        duration = m.video.duration
    else:
        video_info = subprocess.check_output(f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{file_dl_path}"', shell=True).decode()
        fields = json.loads(video_info)['streams'][0]
        duration = int(fields['duration'].split(".")[0])
    sub_count = 0
    repeated_count = 0
    last_text = " "
    duplicate = True
    lastsub_time = 0
    intervals = [round(num, 2) for num in np.linspace(0,duration,(duration-0)*int(1/0.1)+1).tolist()]
    time_to_finish = duration
    # Extract frames every 100 milliseconds for ocr
    for interval in intervals:
        command = os.system(f'ffmpeg -ss {interval} -i "{file_dl_path}" -pix_fmt yuvj422p -vframes 1 -q:v 2 -y temp/output.jpg')
        if command != 0:
            return await ms.delete()
        try:
            im = Image.open("temp/output.jpg")
            text = pytesseract.image_to_string(im, LANG)
        except:
            text = None
            pass
        if time_to_finish > 0:
            time_to_finish -= 0.1
            percentage = (duration - time_to_finish) * 100 / duration
            progress = "[{0}{1}]\nPercentage : {2}%\n\n".format(
                ''.join(["●" for i in range(math.floor(percentage / 5))]),
                ''.join(["○" for i in range(20 - math.floor(percentage / 5))]),
                round(percentage, 2)
            )
            try:
                await ms.edit(progress + "`For cancel progress, send` /cancel", parse_mode='md')
            except:
                pass
        if text != None and text[:1].isspace() == False :
            # Check either text is duplicate or not
            commons = list(set(text.rsplit()) & set(last_text.rsplit()))
            if len(text.rsplit()) < 3 and len(commons) >= 1:
                duplicate = True
                repeated_count += 1
            elif len(text.rsplit()) >= 3 and len(commons) >= 3:
                duplicate = True
                repeated_count += 1
            else:
                duplicate = False

            # time of the last dialogue
            if duplicate == False:
                lastsub_time = interval
                
            # Write the dialogues text
            if repeated_count != 0 and duplicate == False:
                sub_count += 1
                from_time = str(datetime.datetime.fromtimestamp(interval-0.1-repeated_count*0.1)+datetime.timedelta(hours=0)).split(' ')[1][:12]
                to_time = str(datetime.datetime.fromtimestamp(interval)+datetime.timedelta(hours=0)).split(' ')[1][:12]
                from_time = f"{from_time}.000" if not "." in from_time else from_time
                to_time = f"{to_time}.000" if not "." in to_time else to_time
                f = open("temp/srt.srt", "a+", encoding="utf-8")
                f.write(str(sub_count) + "\n" + from_time + " --> " + to_time + "\n" + last_text + "\n\n")
                duplicate = True
                repeated_count = 0
            last_text = text

        # Write the last dialogue
        if interval == duration:
            ftime = str(datetime.datetime.fromtimestamp(lastsub_time)+datetime.timedelta(hours=0)).split(' ')[1][:12]
            ttime = str(datetime.datetime.fromtimestamp(lastsub_time+10)+datetime.timedelta(hours=0)).split(' ')[1][:12]
            ftime = f"{ftime}.000" if not "." in ftime else ftime
            ttime = f"{ttime}.000" if not "." in ttime else ttime
            f = open("temp/srt.srt", "a+", encoding="utf-8")
            f.write(str(sub_count+1) + "\n" + ftime + " --> " + ttime + "\n" + last_text + "\n\n")

    f.close
    await bot.send_document(chat_id=m.chat.id, document="temp/srt.srt", file_name=media.file_name.rsplit('.', 1)[0]+".srt")


Bot.run()
