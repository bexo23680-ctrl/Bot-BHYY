import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from database import Database
import uuid

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة قاعدة البيانات
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start - يرسل رسالة ترحيبية مع معرف المستخدم المجهول"""
    user = update.effective_user
    user_id = user.id
    
    # الحصول على أو إنشاء معرف مجهول للمستخدم
    anonymous_id = db.get_or_create_user(user_id, user.username)
    
    welcome_message = f"""
🎭 *مرحباً بك في بوت المراسلة المجهولة!*

🔒 المعرف المجهول الخاص بك: `{anonymous_id}`

📝 *كيفية الاستخدام:*
- أرسل `/link` للحصول على رابطك الخاص لاستقبال الرسائل
- استخدم الرابط الخاص بشخص آخر لإرسال رسالة مجهولة له
- أرسل `/myid` لمعرفة معرفك المجهول
- استخدم `/help` للمساعدة

⚠️ *تنبيه:* البوت لا يحتفظ بهوية المرسل، لكن يرجى استخدام الخدمة بمسؤولية.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔗 الحصول على رابطي", callback_data="get_link")],
        [InlineKeyboardButton("ℹ️ معرفي المجهول", callback_data="my_id")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help - يعرض المساعدة"""
    help_text = """
📚 *دليل استخدام البوت*

1️⃣ *لاستقبال الرسائل المجهولة:*
   - أرسل `/link` لتحصل على رابطك الخاص
   - شارك هذا الرابط مع أصدقائك

2️⃣ *لإرسال رسالة مجهولة:*
   - احصل على رابط صديقك
   - افتح الرابط وسيبدأ البوت تلقائياً
   - أرسل رسالتك وستصل لصديقك دون الكشف عن هويتك

3️⃣ *أوامر إضافية:*
   - `/start` - تشغيل البوت
   - `/link` - الحصول على رابطك
   - `/myid` - معرفك المجهول
   - `/stats` - إحصائيات رسائلك
   - `/block` - حظر/إلغاء حظر استقبال الرسائل

⚠️ *تنبيه مهم:* 
الرجاء استخدام البوت بمسؤولية وعدم إرسال محتوى مسيء.
سيتم حظر المخالفين نهائياً.
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /myid - يعرض المعرف المجهول للمستخدم"""
    user_id = update.effective_user.id
    anonymous_id = db.get_anonymous_id(user_id)
    
    if anonymous_id:
        await update.message.reply_text(
            f"🔒 المعرف المجهول الخاص بك: `{anonymous_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ حدث خطأ. أعد تشغيل البوت باستخدام /start")

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /link - يرسل رابط المستخدم المجهول"""
    user_id = update.effective_user.id
    anonymous_id = db.get_anonymous_id(user_id)
    
    if anonymous_id:
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={anonymous_id}"
        
        keyboard = [[InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔗 *رابطك المجهول:*\n`{link}`\n\nشارك هذا الرابط مع أصدقائك ليتمكنوا من مراسلتك مجهولاً!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ حدث خطأ. أعد تشغيل البوت باستخدام /start")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /stats - يعرض إحصائيات المستخدم"""
    user_id = update.effective_user.id
    user_stats = db.get_user_stats(user_id)
    
    if user_stats:
        sent_count = user_stats['sent']
        received_count = user_stats['received']
        is_blocked = user_stats['blocked']
        
        stats_text = f"""
📊 *إحصائياتك:*

✉️ الرسائل المرسلة: {sent_count}
📨 الرسائل المستلمة: {received_count}
🚫 حالة استقبال الرسائل: {'موقوف ❌' if is_blocked else 'مفعل ✅'}

{f"⚠️ أنت محظور من استقبال الرسائل. استخدم /block لإلغاء الحظر." if is_blocked else ""}
"""
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ حدث خطأ. أعد تشغيل البوت باستخدام /start")

async def toggle_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /block - تبديل حالة استقبال الرسائل"""
    user_id = update.effective_user.id
    current_status = db.toggle_block(user_id)
    
    status_text = "تم إيقاف استقبال الرسائل المجهولة 🚫" if current_status else "تم تفعيل استقبال الرسائل المجهولة ✅"
    await update.message.reply_text(status_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية - المنطق الرئيسي للبوت"""
    if not update.message or not update.message.text:
        return
    
    sender_id = update.effective_user.id
    message_text = update.message.text
    
    # التحقق مما إذا كان المستخدم في جلسة إرسال (بدأ من رابط)
    if 'recipient_id' in context.user_data:
        recipient_anonymous_id = context.user_data['recipient_id']
        
        # الحصول على معرف المستلم الحقيقي
        recipient_real_id = db.get_user_by_anonymous_id(recipient_anonymous_id)
        
        if recipient_real_id:
            # التحقق من أن المستلم لم يحظر الرسائل
            if db.is_blocked(recipient_real_id):
                await update.message.reply_text("❌ هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً.")
            else:
                # إرسال الرسالة المجهولة
                try:
                    await context.bot.send_message(
                        chat_id=recipient_real_id,
                        text=f"📨 *رسالة مجهولة جديدة:*\n\n{message_text}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # تسجيل الرسالة
                    db.record_message(sender_id, recipient_real_id)
                    
                    # تأكيد الإرسال
                    keyboard = [[InlineKeyboardButton("📤 إرسال رسالة أخرى", callback_data=f"send_again_{recipient_anonymous_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        "✅ *تم إرسال رسالتك المجهولة بنجاح!*",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    await update.message.reply_text("❌ حدث خطأ أثناء إرسال الرسالة. قد يكون المستخدم قد حذف حسابه.")
        else:
            await update.message.reply_text("❌ رابط غير صالح أو منتهي الصلاحية.")
        
        # تنظيف الجلسة
        if 'recipient_id' in context.user_data:
            del context.user_data['recipient_id']
        
        return
    
    # إذا لم يكن في جلسة إرسال، مجرد رد عادي
    await update.message.reply_text(
        "👋 أهلاً! أرسل /start لبدء استخدام البوت أو /help للمساعدة."
    )

async def handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الروابط العميقة (deep links)"""
    if context.args and len(context.args) > 0:
        anonymous_id = context.args[0]
        
        # تخزين معرف المستلم في بيانات المستخدم
        context.user_data['recipient_id'] = anonymous_id
        
        await update.message.reply_text(
            f"✉️ *أنت الآن ترسل رسالة مجهولة*\n\n"
            f"اكتب رسالتك وسيتم إرسالها مباشرة.\n"
            f"لإلغاء العملية، أرسل /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /cancel - إلغاء عملية الإرسال"""
    if 'recipient_id' in context.user_data:
        del context.user_data['recipient_id']
        await update.message.reply_text("✅ تم إلغاء عملية الإرسال.")
    else:
        await update.message.reply_text("❌ لا توجد عملية إرسال نشطة للإلغاء.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة المفاتيح المضمنة"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_link":
        user_id = query.from_user.id
        anonymous_id = db.get_anonymous_id(user_id)
        
        if anonymous_id:
            bot_username = context.bot.username
            link = f"https://t.me/{bot_username}?start={anonymous_id}"
            await query.edit_message_text(
                f"🔗 *رابطك المجهول:*\n`{link}`\n\nشاركه مع أصدقائك!",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "my_id":
        user_id = query.from_user.id
        anonymous_id = db.get_anonymous_id(user_id)
        
        if anonymous_id:
            await query.edit_message_text(
                f"🔒 المعرف المجهول الخاص بك: `{anonymous_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data.startswith("send_again_"):
        anonymous_id = query.data.replace("send_again_", "")
        context.user_data['recipient_id'] = anonymous_id
        
        await query.edit_message_text(
            "✉️ أرسل رسالتك الجديدة الآن."
        )

def main():
    """تشغيل البوت"""
    # الحصول على التوكن من متغيرات البيئة
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        logger.error("لم يتم العثور على TELEGRAM_BOT_TOKEN في متغيرات البيئة!")
        return
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", handle_deep_link))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myid", my_id))
    application.add_handler(CommandHandler("link", get_link))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("block", toggle_block))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # تشغيل البوت
    logger.info("تم تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
