// Frontend/src/pages/TermsOfServicePage.tsx
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";

export default function TermsOfServicePage() {
  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Gebruiksvoorwaarden"
        subtitle="De regels voor het gebruik van Turkspot"
        maxWidth="4xl"
      >
        <Card>
          <CardContent className="prose prose-sm max-w-none p-6 text-foreground dark:prose-invert">
            <h2>1. Aanvaarding van de voorwaarden</h2>
            <p>
              Door toegang te krijgen tot en gebruik te maken van Turkspot ("de App", "de Dienst"), 
              ga je akkoord met deze gebruiksvoorwaarden. Als je niet akkoord gaat met deze voorwaarden, 
              gebruik de App dan niet.
            </p>

            <h2>2. Beschrijving van de dienst</h2>
            <p>
              Turkspot is een platform dat de Turkse diaspora in Nederland verbindt door middel van:
            </p>
            <ul>
              <li>Een kaart met Turkse bedrijven en locaties</li>
              <li>Nieuws en evenementen relevant voor de diaspora</li>
              <li>Community interacties (check-ins, reacties, notities, polls)</li>
              <li>Trending en analytics features</li>
            </ul>

            <h2>3. Account registratie</h2>
            <p>Om bepaalde features te gebruiken, moet je mogelijk een account aanmaken. Je bent verantwoordelijk voor:</p>
            <ul>
              <li>Het behoud van de vertrouwelijkheid van je accountgegevens</li>
              <li>Alle activiteiten die plaatsvinden onder je account</li>
              <li>Het onmiddellijk melden van ongeautoriseerd gebruik</li>
            </ul>

            <h2>4. Gebruikersgedrag</h2>
            <p>Je stemt ermee in dat je:</p>
            <ul>
              <li>Geen onwettige activiteiten zult uitvoeren</li>
              <li>Geen schadelijke, bedreigende, beledigende of discriminerende inhoud zult delen</li>
              <li>De rechten van anderen zult respecteren (privacy, intellectueel eigendom)</li>
              <li>Geen spam, malware of andere schadelijke code zult verspreiden</li>
              <li>De App niet zult gebruiken voor commerciële doeleinden zonder toestemming</li>
            </ul>

            <h2>5. Inhoud van gebruikers</h2>
            <p>
              Door inhoud te delen op Turkspot (notities, reacties, check-ins), geef je ons een licentie 
              om deze inhoud te gebruiken, te tonen en te distribueren binnen de App. 
              Je behoudt alle rechten op jouw inhoud.
            </p>

            <h2>6. Intellectueel eigendom</h2>
            <p>
              Alle rechten, titel en eigendom in en op de App, inclusief maar niet beperkt tot software, 
              graphics, logo's en merken, zijn eigendom van Turkspot of onze licentiegevers.
            </p>

            <h2>7. Beschikbaarheid van de dienst</h2>
            <p>
              We streven ernaar de App 24/7 beschikbaar te houden, maar garanderen dit niet. 
              De App kan tijdelijk niet beschikbaar zijn voor onderhoud, updates of om andere redenen.
            </p>

            <h2>8. Disclaimers</h2>
            <p>
              De App wordt geleverd "zoals het is", zonder enige garantie. 
              We zijn niet aansprakelijk voor:
            </p>
            <ul>
              <li>Nauwkeurigheid, volledigheid of actualiteit van de informatie</li>
              <li>Schade als gevolg van het gebruik of onvermogen om de App te gebruiken</li>
              <li>Inhoud van gebruikers of derden</li>
            </ul>

            <h2>9. Beperking van aansprakelijkheid</h2>
            <p>
              Voor zover toegestaan door de wet, zijn wij niet aansprakelijk voor indirecte, incidentele, 
              speciale, gevolg- of voorbeeldschade, inclusief verlies van winst of gegevens.
            </p>

            <h2>10. Opzegging</h2>
            <p>
              Je kunt je account op elk moment opzeggen. 
              Wij behouden ons het recht voor om accounts te schorsen of te beëindigen die deze voorwaarden schenden.
            </p>

            <h2>11. Wijzigingen in de voorwaarden</h2>
            <p>
              We kunnen deze gebruiksvoorwaarden van tijd tot tijd wijzigen. 
              Belangrijke wijzigingen zullen we communiceren via de App of e-mail. 
              Door gebruik te blijven maken van de App na wijzigingen, ga je akkoord met de nieuwe voorwaarden.
            </p>

            <h2>12. Toepasselijk recht</h2>
            <p>
              Deze voorwaarden worden beheerst door en geïnterpreteerd in overeenstemming met het Nederlands recht. 
              Geschillen zullen worden voorgelegd aan de bevoegde rechter in Nederland.
            </p>

            <h2>13. Contact</h2>
            <p>
              Voor vragen over deze gebruiksvoorwaarden, neem contact met ons op via: 
              <a href="mailto:legal@turkishdiaspora.app">legal@turkishdiaspora.app</a>
            </p>

            <p className="text-sm text-muted-foreground mt-6">
              Laatste update: {new Date().toLocaleDateString("nl-NL", { year: "numeric", month: "long", day: "numeric" })}
            </p>
          </CardContent>
        </Card>
      </PageShell>
    </AppViewportShell>
  );
}




















