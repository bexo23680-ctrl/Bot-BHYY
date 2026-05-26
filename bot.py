import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
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

# حالات المحادثة للبحث عن مستخدم
SEARCH_USER = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start - يرسل رسالة ترحيبية مع معرف المستخدم المجهول"""
    user = update.effective_user
    user_id = user.id
    
    # الحصول على أو إنشاء معرف مجهول للمستخدم
    anonymous_id = db.get_or_create_user(user_id, user.username)
    
    # التحقق مما إذا كان المستخدم قادماً من رابط
    if context.args and len(context.args) > 0:
        await handle_deep_link(update, context)
        return
    
    welcome_message = f"""
🎭 *مرحباً بك في بوت المراسلة المجهولة!*

🔒 المعرف المجهول الخاص بك: `{anonymous_id}`

📝 *اختر من القائمة:*
"""
    
    keyboard = [
        [InlineKeyboardButton("📤 إرسال رسالة مجهولة", callback_data="send_anonymous")],
        [InlineKeyboardButton("📨 استقبال الرسائل", callback_data="receive_messages")],
        [InlineKeyboardButton("🔗 الحصول على رابطي", callback_data="get_link")],
        [InlineKeyboardButton("ℹ️ معرفي المجهول", callback_data="my_id")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
        [InlineKeyboardButton("🚫 حظر/تفعيل الاستقبال", callback_data="toggle_block")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("📤 إرسال رسالة مجهولة", callback_data="send_anonymous")],
        [InlineKeyboardButton("📨 استقبال الرسائل", callback_data="receive_messages")],
        [InlineKeyboardButton("🔗 الحصول على رابطي", callback_data="get_link")],
        [InlineKeyboardButton("ℹ️ معرفي المجهول", callback_data="my_id")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
        [InlineKeyboardButton("🚫 حظر/تفعيل الاستقبال", callback_data="toggle_block")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎭 *القائمة الرئيسية*\nاختر ما تريد القيام به:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help - يعرض المساعدة"""
    help_text = """
📚 *دليل استخدام البوت*

1️⃣ *لإرسال رسالة مجهولة:*
   - اضغط على "📤 إرسال رسالة مجهولة"
   - أدخل المعرف المجهول للشخص
   - اكتب رسالتك وستصل دون الكشف عن هويتك

2️⃣ *لاستقبال الرسائل المجهولة:*
   - اضغط على "📨 استقبال الرسائل"
   - سترى أحدث الرسائل المجهولة التي وصلتك
   - يمكنك الرد على الرسائل

3️⃣ *مشاركة معرفك:*
   - اضغط على "🔗 الحصول على رابطي" لمشاركته
   - أو "ℹ️ معرفي المجهول" لرؤيته

4️⃣ *أوامر إضافية:*
   - /start - تشغيل البوت
   - /menu - القائمة الرئيسية
   - /cancel - إلغاء العملية الحالية

⚠️ *تنبيه مهم:* 
الرجاء استخدام البوت بمسؤولية وعدم إرسال محتوى مسيء.
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /myid - يعرض المعرف المجهول للمستخدم"""
    user_id = update.effective_user.id
    anonymous_id = db.get_anonymous_id(user_id)
    
    if anonymous_id:
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔒 المعرف المجهول الخاص بك: `{anonymous_id}`\n\n"
            f"شارك هذا المعرف مع أصدقائك لاستقبال رسائلهم!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
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
        
        keyboard = [
            [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}")],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔗 *رابطك المجهول:*\n`{link}`\n\n"
            f"شارك هذا الرابط مع أصدقائك ليتمكنوا من مراسلتك مجهولاً!\n\n"
            f"أو يمكنهم استخدام معرفك: `{anonymous_id}` للبحث عنك في البوت.",
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

{f"⚠️ أنت محظور من استقبال الرسائل. استخدم زر 'حظر/تفعيل الاستقبال' لإلغاء الحظر." if is_blocked else ""}
"""
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ حدث خطأ. أعد تشغيل البوت باستخدام /start")

async def toggle_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /block - تبديل حالة استقبال الرسائل"""
    user_id = update.effective_user.id
    current_status = db.toggle_block(user_id)
    
    status_text = "تم إيقاف استقبال الرسائل المجهولة 🚫" if current_status else "تم تفعيل استقبال الرسائل المجهولة ✅"
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(status_text, reply_markup=reply_markup)

async def receive_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الرسائل المستلمة للمستخدم"""
    user_id = update.effective_user.id
    
    # جلب أحدث 10 رسائل مستلمة
    recent_messages = db.get_received_messages(user_id, limit=10)
    
    if not recent_messages:
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📭 *لا توجد رسائل بعد*\n\n"
            "شارك معرفك المجهول أو رابطك مع أصدقائك لاستقبال رسائل مجهولة!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    messages_text = "📨 *أحدث رسائلك المجهولة:*\n\n"
    
    for i, msg in enumerate(recent_messages, 1):
        # اقتطاع الرسالة إذا كانت طويلة
        preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        messages_text += f"{i}. {preview}\n"
        messages_text += f"   📅 _{msg['date']}_\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📋 عرض رسالة كاملة", callback_data="view_full_messages")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        messages_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def view_full_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الرسائل كاملة واحدة تلو الأخرى"""
    user_id = update.effective_user.id
    
    # تخزين قائمة الرسائل في بيانات المستخدم للتنقل
    if 'message_index' not in context.user_data:
        context.user_data['message_index'] = 0
        context.user_data['messages'] = db.get_received_messages(user_id, limit=10)
    
    messages = context.user_data.get('messages', [])
    current_index = context.user_data.get('message_index', 0)
    
    if not messages:
        await update.message.reply_text("لا توجد رسائل للعرض.")
        return
    
    if current_index < len(messages):
        msg = messages[current_index]
        message_text = f"""
📨 *رسالة مجهولة* ({current_index + 1}/{len(messages)})

📝 *المحتوى:*
{msg['content']}

📅 *التاريخ:* {msg['date']}
"""
        keyboard = []
        
        # أزرار التنقل بين الرسائل
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="prev_message"))
        if current_index < len(messages) - 1:
            nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="next_message"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("📤 رد برسالة", callback_data=f"reply_to_{current_index}")])
        keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("لا توجد رسائل إضافية.")

async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية البحث عن مستخدم"""
    await update.message.reply_text(
        "🔍 *البحث عن مستخدم*\n\n"
        "أدخل المعرف المجهول للشخص الذي تريد مراسلته:\n"
        "(لإلغاء العملية أرسل /cancel)",
        parse_mode=ParseMode.MARKDOWN
    )
    return SEARCH_USER

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة المعرف المدخل والبحث عن المستخدم"""
    anonymous_id = update.message.text.strip()
    
    # البحث عن المستخدم
    user = db.get_user_by_anonymous_id(anonymous_id)
    
    if user:
        user_id = user['user_id']
        
        # التحقق من أن المستخدم ليس محظوراً
        if db.is_blocked(user_id):
            await update.message.reply_text(
                "🚫 هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")
                ]])
            )
            return ConversationHandler.END
        
        # تخزين معرف المستلم
        context.user_data['recipient_id'] = anonymous_id
        
        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ تم العثور على المستخدم!\n\n"
            f"✉️ *اكتب رسالتك الآن وسيتم إرسالها مباشرة.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    else:
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ لم يتم العثور على مستخدم بهذا المعرف.\n"
            "تأكد من المعرف وحاول مرة أخرى.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية - المنطق الرئيسي للبوت"""
    if not update.message or not update.message.text:
        return
    
    sender_id = update.effective_user.id
    message_text = update.message.text
    
    # التحقق مما إذا كان المستخدم في جلسة إرسال
    if 'recipient_id' in context.user_data:
        recipient_anonymous_id = context.user_data['recipient_id']
        
        # الحصول على معرف المستلم الحقيقي
        recipient_data = db.get_user_by_anonymous_id(recipient_anonymous_id)
        
        if recipient_data:
            recipient_real_id = recipient_data['user_id']
            
            # التحقق من أن المستلم لم يحظر الرسائل
            if db.is_blocked(recipient_real_id):
                await update.message.reply_text("❌ هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً.")
            else:
                # إرسال الرسالة المجهولة
                try:
                    await context.bot.send_message(
                        chat_id=recipient_real_id,
                        text=f"📨 *رسالة مجهولة جديدة:*\n\n{message_text}\n\n💡 للرد أو الاطلاع على رسائلك، استخدم /start",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # تسجيل الرسالة
                    db.record_message(sender_id, recipient_real_id, message_text)
                    
                    # تأكيد الإرسال
                    keyboard = [
                        [InlineKeyboardButton("📤 إرسال رسالة أخرى", callback_data=f"send_again_{recipient_anonymous_id}")],
                        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
                    ]
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
    
    # تنظيف بيانات التنقل بين الرسائل
    if 'message_index' in context.user_data:
        del context.user_data['message_index']
    if 'messages' in context.user_data:
        del context.user_data['messages']
    
    await update.message.reply_text("✅ تم إلغاء العملية.")
    await main_menu(update, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة المفاتيح المضمنة"""
    query = update.callback_query
    await query.answer()
    
    # العودة للقائمة الرئيسية
    if query.data == "back_to_menu":
        # تنظيف البيانات المؤقتة
        if 'message_index' in context.user_data:
            del context.user_data['message_index']
        if 'messages' in context.user_data:
            del context.user_data['messages']
        if 'recipient_id' in context.user_data:
            del context.user_data['recipient_id']
        
        await query.message.delete()
        await main_menu(query, context)
        return
    
    # إرسال رسالة مجهولة
    elif query.data == "send_anonymous":
        await query.message.delete()
        await search_user_start(query, context)
        return
    
    # استقبال الرسائل
    elif query.data == "receive_messages":
        await query.message.delete()
        await receive_messages(query, context)
        return
    
    # عرض الرسائل الكاملة
    elif query.data == "view_full_messages":
        await query.message.delete()
        await view_full_messages(query, context)
        return
    
    # التنقل بين الرسائل
    elif query.data == "next_message":
        if 'message_index' in context.user_data:
            context.user_data['message_index'] += 1
        await query.message.delete()
        await view_full_messages(query, context)
        return
    
    elif query.data == "prev_message":
        if 'message_index' in context.user_data:
            context.user_data['message_index'] -= 1
        await query.message.delete()
        await view_full_messages(query, context)
        return
    
    # الرد على رسالة
    elif query.data.startswith("reply_to_"):
        index = int(query.data.replace("reply_to_", ""))
        messages = context.user_data.get('messages', [])
        if messages and index < len(messages):
            # هنا يمكنك إضافة منطق الرد على رسالة محددة
            await query.message.reply_text(
                "📝 *ميزة الرد قيد التطوير*\n"
                "يمكنك إرسال رسالة جديدة باستخدام معرف المستخدم.",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # إلغاء الإرسال
    elif query.data == "cancel_send":
        if 'recipient_id' in context.user_data:
            del context.user_data['recipient_id']
        await query.message.delete()
        await query.message.reply_text("✅ تم إلغاء عملية الإرسال.")
        await main_menu(query, context)
        return
    
    # الحصول على الرابط
    elif query.data == "get_link":
        user_id = query.from_user.id
        anonymous_id = db.get_anonymous_id(user_id)
        
        if anonymous_id:
            bot_username = context.bot.username
            link = f"https://t.me/{bot_username}?start={anonymous_id}"
            
            keyboard = [
                [InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🔗 *رابطك المجهول:*\n`{link}`\n\n"
                f"أو استخدم معرفك: `{anonymous_id}` للبحث المباشر",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    # معرفي المجهول
    elif query.data == "my_id":
        user_id = query.from_user.id
        anonymous_id = db.get_anonymous_id(user_id)
        
        if anonymous_id:
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🔒 المعرف المجهول الخاص بك: `{anonymous_id}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    # الإحصائيات
    elif query.data == "stats":
        user_id = query.from_user.id
        await stats(query, context)
    
    # تبديل الحظر
    elif query.data == "toggle_block":
        user_id = query.from_user.id
        await toggle_block(query, context)
    
    # إرسال رسالة أخرى لنفس المستلم
    elif query.data.startswith("send_again_"):
        anonymous_id = query.data.replace("send_again_", "")
        context.user_data['recipient_id'] = anonymous_id
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✉️ اكتب رسالتك الجديدة الآن.",
            reply_markup=reply_markup
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
    
    # إنشاء محادثة البحث عن مستخدم
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_user_start, pattern="^send_anonymous$")],
        states={
            SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_user)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", handle_deep_link))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", main_menu))
    application.add_handler(CommandHandler("myid", my_id))
    application.add_handler(CommandHandler("link", get_link))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("block", toggle_block))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # إضافة معالج المحادثة
    application.add_handler(search_conv)
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # تشغيل البوت
    logger.info("تم تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
