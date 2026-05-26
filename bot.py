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

# حالات المحادثة
SEARCH_USER = 1
SEND_MESSAGE = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start - يرسل رسالة ترحيبية مع القائمة الرئيسية"""
    user = update.effective_user
    user_id = user.id
    
    # الحصول على أو إنشاء معرف مجهول للمستخدم
    anonymous_id = db.get_or_create_user(user_id, user.username)
    
    # تنظيف أي بيانات مؤقتة
    context.user_data.clear()
    
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
    
    # التحقق مما إذا كان المستخدم قادماً من رابط عميق
    if context.args and len(context.args) > 0:
        anonymous_id = context.args[0]
        context.user_data['recipient_id'] = anonymous_id
        
        await update.message.reply_text(
            f"✉️ *أنت الآن ترسل رسالة مجهولة*\n\n"
            f"اكتب رسالتك وسيتم إرسالها مباشرة.\n"
            f"لإلغاء العملية، استخدم زر الإلغاء أو أرسل /cancel",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")
            ]])
        )
        return
    
    await update.message.reply_text(
        welcome_message,
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

3️⃣ *مشاركة معرفك:*
   - اضغط على "🔗 الحصول على رابطي" لمشاركته
   - أو "ℹ️ معرفي المجهول" لرؤيته

4️⃣ *أوامر إضافية:*
   - /start - تشغيل البوت
   - /cancel - إلغاء العملية الحالية
   - /help - هذه المساعدة

⚠️ *تنبيه مهم:* 
الرجاء استخدام البوت بمسؤولية وعدم إرسال محتوى مسيء.
"""
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية الحالية"""
    # تنظيف جميع البيانات المؤقتة
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ تم إلغاء العملية.",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع أزرار البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"Button pressed: {callback_data} by user {user_id}")
    
    try:
        # العودة للقائمة الرئيسية
        if callback_data == "back_to_menu":
            context.user_data.clear()
            
            keyboard = [
                [InlineKeyboardButton("📤 إرسال رسالة مجهولة", callback_data="send_anonymous")],
                [InlineKeyboardButton("📨 استقبال الرسائل", callback_data="receive_messages")],
                [InlineKeyboardButton("🔗 الحصول على رابطي", callback_data="get_link")],
                [InlineKeyboardButton("ℹ️ معرفي المجهول", callback_data="my_id")],
                [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
                [InlineKeyboardButton("🚫 حظر/تفعيل الاستقبال", callback_data="toggle_block")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🎭 *القائمة الرئيسية*\nاختر ما تريد القيام به:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        
        # إرسال رسالة مجهولة - بدء البحث
        elif callback_data == "send_anonymous":
            context.user_data.clear()
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🔍 *البحث عن مستخدم*\n\n"
                "أدخل المعرف المجهول للشخص الذي تريد مراسلته:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            # تعيين حالة البحث
            context.user_data['state'] = 'searching'
        
        # استقبال الرسائل
        elif callback_data == "receive_messages":
            recent_messages = db.get_received_messages(user_id, limit=10)
            
            if not recent_messages:
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📭 *لا توجد رسائل بعد*\n\n"
                    "شارك معرفك المجهول أو رابطك مع أصدقائك لاستقبال رسائل مجهولة!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                messages_text = "📨 *أحدث رسائلك المجهولة:*\n\n"
                
                for i, msg in enumerate(recent_messages, 1):
                    preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                    messages_text += f"*{i}.* {preview}\n"
                    messages_text += f"   📅 _{msg['date']}_\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("📋 عرض بتفصيل", callback_data="view_full_messages")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # تخزين الرسائل في بيانات المستخدم
                context.user_data['messages'] = recent_messages
                context.user_data['message_index'] = 0
                
                await query.edit_message_text(
                    messages_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # عرض الرسائل الكاملة
        elif callback_data == "view_full_messages":
            messages = context.user_data.get('messages', [])
            current_index = context.user_data.get('message_index', 0)
            
            if not messages:
                await query.edit_message_text(
                    "❌ لا توجد رسائل للعرض.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")
                    ]])
                )
                return
            
            if 0 <= current_index < len(messages):
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
                
                keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # التنقل بين الرسائل
        elif callback_data == "next_message":
            if 'message_index' in context.user_data:
                context.user_data['message_index'] += 1
            # إعادة استدعاء نفس الوظيفة لعرض الرسالة التالية
            await button_callback(update, context)
        
        elif callback_data == "prev_message":
            if 'message_index' in context.user_data:
                context.user_data['message_index'] -= 1
            # إعادة استدعاء نفس الوظيفة لعرض الرسالة السابقة
            await button_callback(update, context)
        
        # الحصول على الرابط
        elif callback_data == "get_link":
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
        elif callback_data == "my_id":
            anonymous_id = db.get_anonymous_id(user_id)
            
            if anonymous_id:
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔒 المعرف المجهول الخاص بك: `{anonymous_id}`\n\n"
                    f"شارك هذا المعرف مع أصدقائك ليتمكنوا من مراسلتك!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # الإحصائيات
        elif callback_data == "stats":
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
"""
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    stats_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        
        # تبديل الحظر
        elif callback_data == "toggle_block":
            current_status = db.toggle_block(user_id)
            status_text = "تم إيقاف استقبال الرسائل المجهولة 🚫" if current_status else "تم تفعيل استقبال الرسائل المجهولة ✅"
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(status_text, reply_markup=reply_markup)
        
        # إلغاء الإرسال
        elif callback_data == "cancel_send":
            context.user_data.clear()
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ تم إلغاء عملية الإرسال.",
                reply_markup=reply_markup
            )
        
        # إرسال رسالة أخرى لنفس المستلم
        elif callback_data.startswith("send_again_"):
            anonymous_id = callback_data.replace("send_again_", "")
            context.user_data['recipient_id'] = anonymous_id
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✉️ اكتب رسالتك الجديدة الآن.",
                reply_markup=reply_markup
            )
        
        else:
            logger.warning(f"Unknown callback data: {callback_data}")
            
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ. الرجاء المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")
            ]])
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الرسائل النصية"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # التحقق من حالة المستخدم
    state = context.user_data.get('state')
    
    # إذا كان المستخدم في حالة بحث عن مستخدم
    if state == 'searching':
        # البحث عن المستخدم بالمعرف المجهول
        user_info = db.get_user_by_anonymous_id(message_text)
        
        if user_info:
            if user_info['is_blocked']:
                keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🚫 هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً.",
                    reply_markup=reply_markup
                )
            else:
                # تخزين معرف المستلم والانتقال لوضع الإرسال
                context.user_data['recipient_id'] = message_text
                context.user_data['state'] = 'sending'
                
                keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_send")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ تم العثور على المستخدم!\n\n"
                    f"✉️ *اكتب رسالتك الآن وسيتم إرسالها مباشرة.*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        else:
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ لم يتم العثور على مستخدم بهذا المعرف.\n"
                "تأكد من المعرف وحاول مرة أخرى.",
                reply_markup=reply_markup
            )
        
        return
    
    # إذا كان المستخدم في حالة إرسال رسالة
    if 'recipient_id' in context.user_data:
        recipient_anonymous_id = context.user_data['recipient_id']
        recipient_info = db.get_user_by_anonymous_id(recipient_anonymous_id)
        
        if recipient_info:
            recipient_real_id = recipient_info['user_id']
            
            # التحقق من أن المستلم لم يحظر الرسائل
            if db.is_blocked(recipient_real_id):
                await update.message.reply_text(
                    "❌ هذا المستخدم أوقف استقبال الرسائل المجهولة حالياً."
                )
            else:
                # إرسال الرسالة المجهولة
                try:
                    await context.bot.send_message(
                        chat_id=recipient_real_id,
                        text=f"📨 *رسالة مجهولة جديدة:*\n\n{message_text}\n\n💡 للرد أو الاطلاع على رسائلك، استخدم /start",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # تسجيل الرسالة
                    db.record_message(user_id, recipient_real_id, message_text)
                    
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
                    await update.message.reply_text(
                        "❌ حدث خطأ أثناء إرسال الرسالة."
                    )
        else:
            await update.message.reply_text(
                "❌ رابط غير صالح أو منتهي الصلاحية."
            )
        
        # تنظيف الجلسة
        context.user_data.clear()
        return
    
    # رسالة افتراضية
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 أهلاً! استخدم القائمة للتنقل أو أرسل /start.",
        reply_markup=reply_markup
    )

def main():
    """تشغيل البوت"""
    # الحصول على التوكن من متغيرات البيئة
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        logger.error("لم يتم العثور على TELEGRAM_BOT_TOKEN في متغيرات البيئة!")
        return
    
    logger.info("جاري تشغيل البوت...")
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر الأساسية أولاً
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # إضافة معالج الأزرار - هذا هو المهم
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # إضافة معالج الرسائل النصية في النهاية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل البوت
    logger.info("البوت جاهز للعمل!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
