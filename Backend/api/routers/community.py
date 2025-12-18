from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/community", tags=["community"])


class CommunityGuidelinesResponse(BaseModel):
    title: str
    content: str
    last_updated: str


@router.get("/guidelines", response_model=CommunityGuidelinesResponse)
async def get_community_guidelines():
    """
    Get community guidelines content.
    Returns static content that can be updated by administrators.
    """
    # For now, return static content. This can be moved to a database table later if needed.
    return CommunityGuidelinesResponse(
        title="Community Richtlijnen",
        content="""
<h2>1. Respect voor elkaar</h2>
<p>We behandelen alle communityleden met respect en waardigheid. Discriminatie, haatzaaien, pesten of intimidatie in welke vorm dan ook wordt niet getolereerd. Wees vriendelijk en respectvol in al je interacties.</p>

<h2>2. Authentieke en nuttige inhoud</h2>
<p>Deel alleen authentieke en nuttige informatie. Spam, misleidende informatie of valse recensies zijn niet toegestaan. Wees eerlijk en transparant in je beoordelingen en notities.</p>

<h2>3. Privacy en veiligheid</h2>
<p>Respecteer de privacy van anderen. Deel geen persoonlijke informatie zonder toestemming. Als je merkt dat iemand je privacy schendt of zich onveilig gedraagt, rapporteer dit.</p>

<h2>4. Commerciële activiteiten</h2>
<p>Zelfpromotie en commerciële activiteiten zijn alleen toegestaan voor bedrijven met een goedgekeurd business account. Ongeautoriseerde advertenties of commerciële berichten zullen worden verwijderd.</p>

<h2>5. Intellectueel eigendom</h2>
<p>Respecteer het intellectueel eigendom van anderen. Deel geen auteursrechtelijk beschermd materiaal zonder toestemming. Gebruik je eigen foto's en content wanneer mogelijk.</p>

<h2>6. Meldingen en rapportages</h2>
<p>Als je inhoud ziet die deze richtlijnen schendt, gebruik dan de rapportagefunctie. We nemen alle meldingen serieus en zullen passende actie ondernemen.</p>

<h2>7. Gevolgen van overtredingen</h2>
<p>Overtreding van deze richtlijnen kan leiden tot waarschuwingen, tijdelijke of permanente schorsing van je account, of verwijdering van inhoud. Ernstige overtredingen kunnen leiden tot een permanente ban.</p>

<h2>8. Samen bouwen</h2>
<p>Deze community is van ons allemaal. Help mee om Turkspot een positieve en welkome plek te maken voor iedereen in de Turkse diaspora. Wees constructief, behulpzaam en vriendelijk.</p>

<h2>9. Vragen of zorgen?</h2>
<p>Heb je vragen over deze richtlijnen of zorgen over de community? Neem contact met ons op via: <a href="mailto:community@turkishdiaspora.app">community@turkishdiaspora.app</a></p>
""",
        last_updated=datetime.now(timezone.utc).isoformat(),
    )



















