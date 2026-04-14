import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "8026261846:AAH1aZcNOVl5cgk6Dw5scGcDJakwQEVJHS0"
ADMIN_ID = 1143938643
ADMIN_ID = 964442694
ADMIN_ID = 8244031255

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Временное хранилище: {admin_id: (user_id, message_id_original)}
# Нужно, чтобы после нажатия "Ответить" знать, кому и в какое сообщение отвечаем
pending_reply = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Приветствуем в поддержке zynx_snos!\n"
        "Отвечаем за 24 часа. Отправьте ваш запрос."
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        return
    text = update.message.text
    if not text:
        return

    user_info = f"@{user.username}" if user.username else f"ID {user.id}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Ответить", callback_data=f"reply_{user.id}_{update.message.message_id}"),
         InlineKeyboardButton("❌ Закрыть", callback_data="close")]
    ])
    admin_msg = (
        f"📩 Новый запрос\n"
        f"Пользователь: {user_info}\n"
        f"ID: {user.id}\n\n"
        f"Текст:\n{text}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=keyboard)
        await update.message.reply_text("✅ Ваш запрос отправлен. Ответим в течение 24 часов.")
    except Exception as e:
        logger.error(f"Ошибка пересылки админу: {e}")
        await update.message.reply_text("❌ Ошибка, попробуйте позже.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Только администратор может использовать эти кнопки.")
        return

    data = query.data
    if data == "close":
        await query.delete_message()
        return

    if data.startswith("reply_"):
        parts = data.split("_")
        user_id = int(parts[1])
        original_msg_id = int(parts[2]) if len(parts) > 2 else None
        # Сохраняем, какому пользователю и какому сообщению админ отвечает
        pending_reply[ADMIN_ID] = (user_id, original_msg_id, query.message.message_id)
        await query.edit_message_text(
            f"✍️ Напишите текст ответа для пользователя `{user_id}`.\n"
            "Просто отправьте сообщение. Для отмены напишите /cancel",
            parse_mode="Markdown"
        )

async def admin_text_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста, который админ пишет после нажатия кнопки «Ответить»"""
    if update.effective_user.id != ADMIN_ID:
        return
    if ADMIN_ID not in pending_reply:
        return

    user_id, original_msg_id, admin_msg_id = pending_reply.pop(ADMIN_ID)
    answer_text = update.message.text
    if answer_text.startswith("/cancel"):
        await update.message.reply_text("❌ Ответ отменён.")
        # Восстанавливаем исходное сообщение с кнопками? Не обязательно
        return

    # Отправляем пользователю
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✉️ *Ответ поддержки:*\n\n{answer_text}",
            parse_mode="Markdown"
        )
        # Уведомляем админа об успехе
        await update.message.reply_text(f"✅ Ответ успешно отправлен пользователю {user_id}.")
        # Дополнительно: пометим исходное сообщение у админа как обработанное (заменим текст)
        try:
            await context.bot.edit_message_text(
                chat_id=ADMIN_ID,
                message_id=admin_msg_id,
                text=f"✅ Обработано: ответ отправлен пользователю {user_id}.\n\nИсходный запрос: ...",
                reply_markup=None
            )
        except:
            pass
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при отправке пользователю {user_id}: {error_msg}")
        await update.message.reply_text(
            f"❌ Не удалось отправить ответ пользователю {user_id}.\n"
            f"Причина: {error_msg}\n\n"
            f"Возможно, пользователь заблокировал бота или не начинал диалог."
        )
        # Возвращаем запрос обратно в ожидание? Необязательно

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and ADMIN_ID in pending_reply:
        del pending_reply[ADMIN_ID]
        await update.message.reply_text("Режим ответа отменён.")
    else:
        await update.message.reply_text("Нет активного режима ответа.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👥 Пользователь: просто напишите текст — он уйдёт в поддержку.\n"
        "👑 Администратор:\n"
        "- При запросе появляются кнопки «Ответить» / «Закрыть»\n"
        "- Нажмите «Ответить», затем напишите текст ответа\n"
        "- /cancel — отменить ожидание ответа"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    # Все сообщения от не-админа -> пересылаем админу
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(user_id=ADMIN_ID), handle_user_message))
    # Кнопки
    app.add_handler(CallbackQueryHandler(button_callback))
    # Текст от админа (если он в режиме ответа)
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), admin_text_reply))

    print("Бот запущен. Админ ID:", ADMIN_ID)
    app.run_polling()

if __name__ == "__main__":
    main()
