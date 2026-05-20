const { SlashCommandBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('ping-user')
        .setDescription('לתייג חבר שלא עונה כדי להציק לו חחח')
        .addUserOption(option => 
            option.setName('target')
                .setDescription('מי המשתמש שאתה רוצה לתייג?')
                .setRequired(true))
        .addIntegerOption(option =>
            option.setName('amount')
                .setDescription('כמה פעמים לתייג אותו? (מקסימום 10)')
                .setRequired(true)),

    async execute(interaction) {
        const targetUser = interaction.options.getUser('target');
        let amount = interaction.options.getInteger('amount');

        // הגבלת כמות ל-10 כדי שדיסקורד לא יחסמו את הבוט על הצפה מהירה מדי (Rate Limit)
        if (amount > 10) amount = 10;
        if (amount < 1) amount = 1;

        // הודעה פרטית רק לך שהבוט התחיל לעבוד
        await interaction.reply({ content: `מתחיל לתייג את ${targetUser} כ-${amount} פעמים...`, ephemeral: true });

        // לולאה שמבצעת את התיוגים
        for (let i = 0; i < amount; i++) {
            // שולח את התיוג בערוץ
            await interaction.channel.send(`נוווו ענה כברררר ${targetUser} !!!`);
            
            // מחכה שנייה אחת (1000 מילישניות) בין תיוג לתיוג כדי שזה יעבוד חלק בלי חסימות
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    },
};
