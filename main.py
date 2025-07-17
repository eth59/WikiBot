from mediawiki import MediaWiki
from mediawiki import exceptions as MediaWikiExceptions
import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import requests
from urllib.parse import quote
from keep_alive import keep_alive

def get_thumbnail(title: str) -> str | None:
    url = (
        "https://fr.wikipedia.org/w/api.php"
        "?action=query"
        "&prop=pageimages"
        "&format=json"
        "&piprop=original"
        f"&titles={quote(title)}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            return page.get("original", {}).get("source")
    return None

async def create_wiki_embed(interaction: discord.Interaction, page) -> tuple[discord.Embed, discord.ui.View]:
    embed = discord.Embed(
        title=page.title,
        url=page.url,
        description=page.summary[:2000],
        color=discord.Color.blue()
    )
    embed.set_footer(
        text=f"Requête par {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url
    )

    thumbnail = get_thumbnail(page.title)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Lire sur Wikipédia", url=page.url))

    return embed, view

# Keep the bot alive
keep_alive()

# Load environment variables from .env file
load_dotenv()

# Initialize the MediaWiki client for French Wikipedia
wikipedia = MediaWiki(lang="fr")


# Initialize the Bot
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commande(s) avec Discord.")
    except Exception as e:
        print(f"Erreur de sync: {e}")
    print(f'Bot is ready as {bot.user}')
    

# Command to search Wikipedia
@tree.command(name="wiki", description="Cherche un article sur Wikipédia")
@app_commands.describe(query="Le terme à rechercher sur Wikipédia")
async def wiki_command(interaction: discord.Interaction, query: str):
    try:
        # Search for the query in Wikipedia
        page = wikipedia.page(query)
        
        if not page:
            embed = discord.Embed(
                title="Aucun résultat trouvé",
                description=f"Aucun article trouvé pour **'{query}'**.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Send the embed and view as a response
        embed, view = await create_wiki_embed(interaction, page)
        await interaction.response.send_message(embed=embed, view=view)
    
    except MediaWikiExceptions.DisambiguationError as e:
        options = '\n'.join(f"• {opt}" for opt in e.options[1:10])  # on en montre 10 max
        embed = discord.Embed(
            title="Page ambiguë",
            description=(
                f"Le terme **'{query}'** est ambigu. Voici quelques suggestions :\n\n{options}"
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except MediaWikiExceptions.PageError:
        embed = discord.Embed(
            title="Page non trouvée",
            description=f"Aucun article trouvé pour **'{query}'**.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        print(f"Erreur lors de la recherche de l'article : {type(e).__name__} : {str(e)}")
        embed = discord.Embed(
            title="Erreur",
            description=f"Une erreur s'est produite lors de la recherche de l'article. Veuillez réessayer plus tard.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        
# Command to get a random article
@tree.command(name="wiki_random", description="Obtenir un article aléatoire de Wikipédia")
async def wiki_random_command(interaction: discord.Interaction):
    try:
        # Get a random page from Wikipedia
        page = wikipedia.page(wikipedia.random())
        
        if not page:
            embed = discord.Embed(
                title="Aucun résultat trouvé",
                description="Aucun article aléatoire trouvé.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Send the embed and view as a response
        embed, view = await create_wiki_embed(interaction, page)
        await interaction.response.send_message(embed=embed, view=view)

    except Exception as e:
        print(f"Erreur lors de la récupération de l'article aléatoire : {type(e).__name__} : {str(e)}")
        embed = discord.Embed(
            title="Erreur",
            description="Une erreur s'est produite lors de la récupération de l'article aléatoire. Veuillez réessayer plus tard.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        

# Command to display help
@tree.command(name="help", description="Affiche les commandes disponibles")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Commandes disponibles",
        description="Voici les commandes que tu peux utiliser avec ce bot :",
        color=discord.Color.green()
    )

    embed.add_field(
        name="/wiki [terme]",
        value="🔍 Recherche un article sur Wikipédia et affiche un résumé avec un lien vers l’article complet.",
        inline=False
    )
    embed.add_field(
        name="/wiki_random",
        value="🎲 Affiche un article aléatoire provenant de Wikipédia.",
        inline=False
    )
    embed.add_field(
        name="/help",
        value="ℹ️ Affiche cette aide.",
        inline=False
    )

    embed.set_footer(text=f"Demandé par {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=True)

        
# Run the bot with the token from environment variable
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("Le token du bot Discord n'est pas défini dans les variables d'environnement.")
    
    bot.run(token)