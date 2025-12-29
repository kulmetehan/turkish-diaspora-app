// Frontend/src/pages/TermsOfServicePage.tsx
import { AppViewportShell, PageShell } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";

export default function TermsOfServicePage() {
  const seo = useSeo();
  return (
    <>
      <SeoHead {...seo} />
      <AppViewportShell variant="content">
      <PageShell
        title="Algemene Voorwaarden"
        subtitle="Voorwaarden voor het gebruik van Turkspot"
        maxWidth="4xl"
      >
        <Card>
          <CardContent className="p-6 md:p-8 lg:p-10">
            <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
              {/* Artikel 1 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">1. Toepasselijkheid</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Deze gebruiksvoorwaarden zijn van toepassing op het gebruik van Turkspot (hierna: "de App" of "de Dienst"). Door de App te gebruiken ga je akkoord met deze voorwaarden. Indien je niet akkoord gaat, dien je de App niet te gebruiken.
                </p>
              </article>

              {/* Artikel 2 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">2. De Dienst</h2>
                <p className="text-base leading-7 text-foreground/90 mb-4">
                  Turkspot is een digitaal platform gericht op de Turkse diaspora in Nederland en biedt onder meer:
                </p>
                <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                  <li>een interactieve kaart met Turkse bedrijven, locaties en organisaties</li>
                  <li>nieuws, evenementen en maatschappelijke initiatieven</li>
                  <li>community-functionaliteiten zoals check-ins, reacties, notities en polls</li>
                  <li>inzichten zoals trending locaties en statistieken</li>
                </ul>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  De Dienst kan in de loop van de tijd worden uitgebreid of aangepast.
                </p>
              </article>

              {/* Artikel 3 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">3. Account en toegang</h2>
                <p className="text-base leading-7 text-foreground/90 mb-4">
                  Voor bepaalde functies is het aanmaken van een account vereist. Dit kan onder andere via e-mail of externe authenticatiediensten zoals Google.
                </p>
                <p className="text-base leading-7 text-foreground/90 font-medium mb-3">
                  Je bent zelf verantwoordelijk voor:
                </p>
                <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                  <li>de juistheid van de door jou verstrekte gegevens</li>
                  <li>het vertrouwelijk houden van je inloggegevens</li>
                  <li>alle activiteiten die plaatsvinden via jouw account</li>
                </ul>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Bij vermoeden van misbruik dien je dit direct te melden.
                </p>
              </article>

              {/* Artikel 4 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">4. Gebruik en gedrag</h2>
                <p className="text-base leading-7 text-foreground/90 mb-4">
                  Het is niet toegestaan om de App te gebruiken voor activiteiten die:
                </p>
                <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                  <li>in strijd zijn met wet- of regelgeving</li>
                  <li>beledigend, discriminerend, bedreigend of misleidend zijn</li>
                  <li>inbreuk maken op de rechten of privacy van anderen</li>
                  <li>spam, malware of andere schadelijke inhoud bevatten</li>
                  <li>zonder toestemming commerciële doeleinden dienen</li>
                </ul>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Wij behouden ons het recht voor om bij misbruik maatregelen te nemen.
                </p>
              </article>

              {/* Artikel 5 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">5. Door gebruikers geplaatste inhoud</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Wanneer je inhoud plaatst in de App (zoals notities, reacties of check-ins), behoud je het eigendom van deze inhoud. Je verleent Turkspot wel een niet-exclusieve licentie om deze inhoud te tonen en te gebruiken binnen de App, uitsluitend in het kader van de Dienst.
                </p>
              </article>

              {/* Artikel 6 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">6. Intellectuele eigendom</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Alle rechten met betrekking tot de App, waaronder software, vormgeving, logo's en merknamen, berusten bij Turkspot of haar licentiegevers. Zonder voorafgaande toestemming is het niet toegestaan deze te kopiëren of te gebruiken.
                </p>
              </article>

              {/* Artikel 7 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">7. Beschikbaarheid</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Wij streven naar een betrouwbare werking van de App, maar kunnen geen ononderbroken beschikbaarheid garanderen. Onderhoud, updates of technische storingen kunnen tijdelijk invloed hebben op de Dienst.
                </p>
              </article>

              {/* Artikel 8 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">8. Aansprakelijkheid</h2>
                <p className="text-base leading-7 text-foreground/90 mb-4">
                  De App wordt aangeboden "zoals deze is". Turkspot is niet aansprakelijk voor:
                </p>
                <ul className="list-disc list-inside space-y-2.5 my-4 ml-4 text-base leading-7 text-foreground/90">
                  <li>onjuistheden of onvolledigheden in content</li>
                  <li>schade voortvloeiend uit het gebruik of niet-kunnen gebruiken van de App</li>
                  <li>door gebruikers of derden geplaatste inhoud</li>
                </ul>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Voor zover wettelijk toegestaan is aansprakelijkheid beperkt.
                </p>
              </article>

              {/* Artikel 9 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">9. Beëindiging</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Je kunt je account op elk moment beëindigen. Wij behouden ons het recht voor accounts te schorsen of te verwijderen bij overtreding van deze voorwaarden.
                </p>
              </article>

              {/* Artikel 10 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">10. Wijzigingen</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Deze voorwaarden kunnen worden aangepast. Bij wezenlijke wijzigingen informeren wij gebruikers via de App of per e-mail. Voortgezet gebruik na wijziging geldt als acceptatie.
                </p>
              </article>

              {/* Artikel 11 */}
              <article className="mb-8 pb-8 border-b border-border last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">11. Toepasselijk recht</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Op deze voorwaarden is Nederlands recht van toepassing. Geschillen worden voorgelegd aan de bevoegde rechter in Nederland.
                </p>
              </article>

              {/* Artikel 12 */}
              <article className="mb-8 pb-8 last:border-0">
                <h2 className="text-xl font-semibold mb-4 mt-0 text-foreground">12. Contact</h2>
                <p className="text-base leading-7 text-foreground/90 m-0">
                  Vragen over deze gebruiksvoorwaarden kun je richten aan:{" "}
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
