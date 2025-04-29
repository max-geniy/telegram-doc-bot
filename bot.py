import logging
import io
import requests
from telegram.ext import Updater, CommandHandler
from telegram import Bot
from pdf2image import convert_from_bytes
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = '7731685613:AAErb4vHAT_rlV57k4CFFpdTFu3QaG1wkHQ'
GROUP_CHAT_ID = -1001234567890
TIMEZONE = 'Europe/Moscow'

# === ДОКУМЕНТЫ И РАСПИСАНИЕ ===
DOCUMENTS = {
    'viezd':     {'id': 'GOOGLE_DOC_ID_NEWS',     'time': '18:00'},  # ежедневно в 18:00
    'zal': {'id': 'GOOGLE_DOC_ID_SCHEDULE', 'time': '14:00'},  # ежедневно в 18:00
    'summary':  {'id': 'GOOGLE_DOC_ID_SUMMARY',  'time': None},     # только вручную
}

# === ЛОГИ ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def download_google_doc_pdf(doc_id):
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    return None

def send_document(bot: Bot, doc_key: str):
    doc_info = DOCUMENTS.get(doc_key)
    if not doc_info:
        logging.warning(f"Документ {doc_key} не найден")
        return

    pdf_data = download_google_doc_pdf(doc_info['id'])
    if not pdf_data:
        logging.error(f"❌ Не удалось скачать документ {doc_key}")
        return

    try:
        images = convert_from_bytes(pdf_data, first_page=1, last_page=1)
        if not images:
            logging.error(f"⚠️ Не удалось конвертировать PDF ({doc_key})")
            return

        img_byte_arr = io.BytesIO()
        images[0].save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        caption = f"🗂 {doc_key.capitalize()} • {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        bot.send_photo(chat_id=GROUP_CHAT_ID, photo=img_byte_arr, caption=caption)
        logging.info(f"✅ Отправлен документ {doc_key}")
    except Exception as e:
        logging.error(f"⚠️ Ошибка при отправке {doc_key}: {str(e)}")

def handle_command(doc_key):
    def command(update, context):
        update.message.reply_text(f"📤 Отправляю тему: {doc_key}...")
        send_document(context.bot, doc_key)
    return command

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Команды по документам
    for key in DOCUMENTS:
        dp.add_handler(CommandHandler(key, handle_command(key)))

    # Команда старт
    dp.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text(
        "Привет! Доступные команды:\n" +
        "\n".join(f"/{k}" for k in DOCUMENTS)
    )))

    # Планировщик
    scheduler = BackgroundScheduler(timezone=pytz.timezone(TIMEZONE))
    for key, data in DOCUMENTS.items():
        if data['time']:
            hour, minute = map(int, data['time'].split(':'))
            scheduler.add_job(lambda k=key: send_document(updater.bot, k),
                              trigger='cron',
                              hour=hour,
                              minute=minute)
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
