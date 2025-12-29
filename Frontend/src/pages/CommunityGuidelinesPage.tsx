// Frontend/src/pages/CommunityGuidelinesPage.tsx
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";

export default function CommunityGuidelinesPage() {
  const seo = useSeo();
  return (
    <>
      <SeoHead {...seo} />
      <AppViewportShell variant="content">
      <PageShell
        title="Community Richtlijnen"
        subtitle="Samen bouwen we een respectvolle en inclusieve community"
        maxWidth="4xl"
      >
        <Card>
          <CardContent className="p-6 md:p-8 lg:p-10">
            <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
              {/* Artikel 1 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">1. Respect voor elkaar</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  We behandelen alle communityleden met respect en waardigheid. Discriminatie, haatzaaien, 
                  pesten of intimidatie in welke vorm dan ook wordt niet getolereerd. Wees vriendelijk en 
                  respectvol in al je interacties.
                </p>
              </article>

              {/* Artikel 2 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">2. Authentieke en nuttige inhoud</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Deel alleen authentieke en nuttige informatie. Spam, misleidende informatie of valse 
                  recensies zijn niet toegestaan. Wees eerlijk en transparant in je beoordelingen en notities.
                </p>
              </article>

              {/* Artikel 3 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">3. Privacy en veiligheid</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Respecteer de privacy van anderen. Deel geen persoonlijke informatie zonder toestemming. 
                  Als je merkt dat iemand je privacy schendt of zich onveilig gedraagt,{" "}
                  <a href="#/account" className="font-medium underline hover:text-primary transition-colors text-foreground">rapporteer dit</a>.
                </p>
              </article>

              {/* Artikel 4 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">4. Commerciële activiteiten</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Zelfpromotie en commerciële activiteiten zijn alleen toegestaan voor bedrijven met een 
                  goedgekeurd business account. Ongeautoriseerde advertenties of commerciële berichten 
                  zullen worden verwijderd.
                </p>
              </article>

              {/* Artikel 5 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">5. Intellectueel eigendom</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Respecteer het intellectueel eigendom van anderen. Deel geen auteursrechtelijk beschermd 
                  materiaal zonder toestemming. Gebruik je eigen foto's en content wanneer mogelijk.
                </p>
              </article>

              {/* Artikel 6 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">6. Meldingen en rapportages</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Als je inhoud ziet die deze richtlijnen schendt, gebruik dan de rapportagefunctie. 
                  We nemen alle meldingen serieus en zullen passende actie ondernemen.{" "}
                  <a href="#/account" className="font-medium underline hover:text-primary transition-colors text-foreground">Leer meer over rapporteren</a>.
                </p>
              </article>

              {/* Artikel 7 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">7. Gevolgen van overtredingen</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Overtreding van deze richtlijnen kan leiden tot waarschuwingen, tijdelijke of permanente 
                  schorsing van je account, of verwijdering van inhoud. Ernstige overtredingen kunnen leiden 
                  tot een permanente ban.
                </p>
              </article>

              {/* Artikel 8 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">8. Samen bouwen</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Deze community is van ons allemaal. Help mee om Turkspot een positieve en welkome plek 
                  te maken voor iedereen in de Turkse diaspora. Wees constructief, behulpzaam en vriendelijk.
                </p>
              </article>

              {/* Artikel 9 */}
              <article className="mb-8 pb-8 last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">9. Vragen of zorgen?</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Heb je vragen over deze richtlijnen of zorgen over de community? Neem contact met ons op via:{" "}
                  <a href="mailto:info@turkspot.app" className="font-medium underline hover:text-primary transition-colors text-foreground">info@turkspot.app</a>
                </p>
              </article>

              {/* Footer */}
              <div className="mt-10 pt-6 border-t border-border">
                <p className="text-sm text-muted-foreground m-0">
                  Laatste update: {new Date().toLocaleDateString("nl-NL", { year: "numeric", month: "long", day: "numeric" })}
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
