// Frontend/src/pages/PrivacyPolicyPage.tsx
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";

export default function PrivacyPolicyPage() {
  const seo = useSeo();
  return (
    <>
      <SeoHead {...seo} />
      <AppViewportShell variant="content">
      <PageShell
        title="Privacybeleid"
        subtitle="Hoe Turkspot omgaat met jouw gegevens"
        maxWidth="4xl"
      >
        <Card>
          <CardContent className="p-6 md:p-8 lg:p-10">
            <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
              {/* Artikel 1 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">1. Inleiding</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Turkspot respecteert jouw privacy en verwerkt persoonsgegevens zorgvuldig en in overeenstemming met de geldende wetgeving (AVG/GDPR). In dit privacybeleid leggen wij uit welke gegevens wij verzamelen en met welk doel.
                </p>
              </article>

              {/* Artikel 2 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">2. Welke gegevens wij verwerken</h2>
                
                <div className="mb-6">
                  <h3 className="text-lg font-medium mb-3 mt-0 text-foreground">2.1 Gegevens die je zelf verstrekt</h3>
                  <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                    <li>accountgegevens zoals naam en e-mailadres</li>
                    <li>profielinformatie (bijvoorbeeld avatar, bio, voorkeuren)</li>
                    <li>inhoud die je plaatst binnen de App (check-ins, reacties, notities, polls)</li>
                  </ul>
                </div>

                <div>
                  <h3 className="text-lg font-medium mb-3 mt-0 text-foreground">2.2 Automatisch verzamelde gegevens</h3>
                  <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                    <li>een anonieme client-ID (soft identity)</li>
                    <li>gebruiks- en interactiegegevens binnen de App</li>
                    <li>technische en statistische gegevens (alleen met toestemming)</li>
                  </ul>
                </div>
              </article>

              {/* Artikel 3 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">3. Doeleinden van verwerking</h2>
                <p className="text-base leading-7 text-foreground/90 mb-4">
                  Wij gebruiken persoonsgegevens uitsluitend om:
                </p>
                <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                  <li>de App en functionaliteiten te leveren</li>
                  <li>community-interacties mogelijk te maken</li>
                  <li>content te personaliseren en te verbeteren</li>
                  <li>statistieken en trends te berekenen</li>
                  <li>ondersteuning en beveiliging te bieden</li>
                </ul>
              </article>

              {/* Artikel 4 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">4. Externe diensten en login</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Bij gebruik van externe loginmethoden (zoals Google) ontvangen wij uitsluitend de noodzakelijke gegevens om authenticatie mogelijk te maken (zoals naam en e-mailadres). Wij gebruiken deze gegevens niet voor andere doeleinden dan accounttoegang.
                </p>
              </article>

              {/* Artikel 5 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">5. Delen van gegevens</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Wij verkopen geen persoonsgegevens. Gegevens worden alleen gedeeld met betrouwbare dienstverleners (zoals hosting of analytics) die noodzakelijk zijn voor de werking van de App, onder strikte verwerkersovereenkomsten.
                </p>
              </article>

              {/* Artikel 6 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">6. Jouw rechten</h2>
                <p className="text-base leading-7 text-foreground/90 mb-4">
                  Je hebt het recht om:
                </p>
                <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                  <li>inzage te krijgen in jouw gegevens</li>
                  <li>gegevens te corrigeren of te verwijderen</li>
                  <li>je account te beëindigen</li>
                  <li>bezwaar te maken tegen bepaalde verwerkingen</li>
                </ul>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Verzoeken kun je indienen via het contactadres hieronder.
                </p>
              </article>

              {/* Artikel 7 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">7. Beveiliging</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Wij nemen passende technische en organisatorische maatregelen om persoonsgegevens te beschermen tegen verlies, misbruik of onbevoegde toegang.
                </p>
              </article>

              {/* Artikel 8 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">8. Bewaartermijnen</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Gegevens worden niet langer bewaard dan noodzakelijk. Bij het verwijderen van je account worden persoonsgegevens binnen redelijke termijn verwijderd, tenzij wettelijke verplichtingen anders vereisen.
                </p>
              </article>

              {/* Artikel 9 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">9. Cookies en tracking</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Turkspot gebruikt uitsluitend functionele cookies. Analytics en tracking zijn opt-in en kunnen via privacy-instellingen worden beheerd.
                </p>
              </article>

              {/* Artikel 10 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">10. Wijzigingen</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Dit privacybeleid kan worden aangepast. Belangrijke wijzigingen communiceren wij via de App of per e-mail.
                </p>
              </article>

              {/* Artikel 11 */}
              <article className="mb-8 pb-8 last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">11. Contact</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Voor vragen over privacy of gegevensverwerking:{" "}
                  <a href="mailto:info@turkspot.app" className="font-medium underline hover:text-primary transition-colors text-foreground">info@turkspot.app</a>
                </p>
              </article>

              {/* Footer */}
              <div className="mt-10 pt-6 border-t border-border">
                <p className="text-sm text-muted-foreground m-0">
                  Laatste update: 29 december 2025
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </PageShell>
    </AppViewportShell>
    </>
  );
}
