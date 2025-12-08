// Frontend/src/pages/PrivacyPolicyPage.tsx
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";

export default function PrivacyPolicyPage() {
  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Privacybeleid"
        subtitle="Hoe we jouw gegevens beschermen en gebruiken"
        maxWidth="4xl"
      >
        <Card>
          <CardContent className="prose prose-sm max-w-none p-6 text-foreground dark:prose-invert">
            <h2>1. Inleiding</h2>
            <p>
              Turkspot ("wij", "ons", "onze") respecteert jouw privacy en is toegewijd aan het beschermen van jouw persoonlijke gegevens. 
              Dit privacybeleid legt uit hoe we jouw gegevens verzamelen, gebruiken, delen en beschermen wanneer je onze app gebruikt.
            </p>

            <h2>2. Gegevens die we verzamelen</h2>
            <h3>2.1 Gegevens die je aan ons verstrekt</h3>
            <ul>
              <li>Account informatie (naam, e-mailadres) bij registratie</li>
              <li>Profiel informatie (avatar, bio, privacy voorkeuren)</li>
              <li>Inhoud die je deelt (check-ins, reacties, notities, poll responses)</li>
            </ul>

            <h3>2.2 Gegevens die automatisch worden verzameld</h3>
            <ul>
              <li>Client ID (anonieme identifier voor soft identity)</li>
              <li>Activiteit data (check-ins, reacties, notities, favorites)</li>
              <li>Gebruiksstatistieken en analytics (opt-in)</li>
            </ul>

            <h2>3. Hoe we jouw gegevens gebruiken</h2>
            <p>We gebruiken jouw gegevens om:</p>
            <ul>
              <li>De app te leveren en te verbeteren</li>
              <li>Jouw activiteit te tonen in de feed en trending</li>
              <li>Gamification features te leveren (XP, badges, streaks)</li>
              <li>Persoonlijke content aan te bevelen</li>
              <li>Technische ondersteuning te bieden</li>
            </ul>

            <h2>4. Delen van gegevens</h2>
            <p>
              We delen jouw gegevens niet met derden voor commerciële doeleinden. 
              Gegevens kunnen gedeeld worden met service providers die ons helpen de app te opereren 
              (bijv. hosting, analytics), onder strikte voorwaarden van vertrouwelijkheid.
            </p>

            <h2>5. Jouw rechten</h2>
            <p>Je hebt het recht om:</p>
            <ul>
              <li>Toegang te krijgen tot jouw persoonlijke gegevens</li>
              <li>Jouw gegevens te corrigeren of bij te werken</li>
              <li>Jouw account te verwijderen en gegevens te laten verwijderen</li>
              <li>Je uit te schrijven voor marketing communicatie</li>
              <li>Bezwaar te maken tegen bepaalde verwerkingen</li>
            </ul>

            <h2>6. Data beveiliging</h2>
            <p>
              We nemen passende technische en organisatorische maatregelen om jouw gegevens te beschermen 
              tegen ongeautoriseerde toegang, wijziging, openbaarmaking of vernietiging.
            </p>

            <h2>7. Data retentie</h2>
            <p>
              We bewaren jouw gegevens zolang als nodig is voor de doeleinden beschreven in dit beleid, 
              of zoals vereist door wetgeving. Je kunt op elk moment je account verwijderen.
            </p>

            <h2>8. Cookies en tracking</h2>
            <p>
              We gebruiken essentiële cookies voor het functioneren van de app. 
              Analytics tracking is opt-in via privacy settings.
            </p>

            <h2>9. Wijzigingen in dit beleid</h2>
            <p>
              We kunnen dit privacybeleid van tijd tot tijd bijwerken. 
              Belangrijke wijzigingen zullen we communiceren via de app of e-mail.
            </p>

            <h2>10. Contact</h2>
            <p>
              Voor vragen over dit privacybeleid of jouw gegevens, neem contact met ons op via: 
              <a href="mailto:privacy@turkishdiaspora.app">privacy@turkishdiaspora.app</a>
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







