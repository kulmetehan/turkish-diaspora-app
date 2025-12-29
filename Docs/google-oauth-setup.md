# Google OAuth Login Setup

## Overzicht

Google OAuth login is geïmplementeerd in de applicatie. Gebruikers kunnen nu inloggen met hun Google account naast de bestaande email/wachtwoord methode.

## Implementatie Details

### Frontend
- **GoogleLoginButton component**: `Frontend/src/components/auth/GoogleLoginButton.tsx`
  - Herbruikbare component voor Google login
  - Handelt OAuth flow af via Supabase
  
- **UserAuthPage**: `Frontend/src/pages/UserAuthPage.tsx`
  - Google login button toegevoegd onder de email/wachtwoord forms
  - OAuth callback handler geïmplementeerd voor account merging
  
- **AccountLoginSection**: `Frontend/src/components/account/AccountLoginSection.tsx`
  - Google login beschikbaar op account pagina voor niet-ingelogde gebruikers

### Backend
- **Account Merge Endpoint**: `Backend/api/routers/auth.py`
  - `/api/v1/auth/check-account-merge` endpoint
  - Checkt of account merging nodig is na OAuth login

## Supabase Configuratie

### 1. Google OAuth Provider Instellen

1. Ga naar Supabase Dashboard → Authentication → Providers
2. Schakel "Google" provider in
3. Vul in:
   - **Client ID (Web application)**: `11401442652-j4q4hi5cr8pmhoijh0elh745a38cmjcd.apps.googleusercontent.com`
   - **Client Secret**: Het secret uit Google Cloud Console (zie Backend/.env)
4. Sla op

### 2. Site URL en Site Name Configureren (BELANGRIJK voor OAuth redirects)

Voor correcte OAuth redirects en branding:

1. Ga naar Supabase Dashboard → Authentication → URL Configuration
2. Stel **Site URL** in op: `https://turkspot.app`
3. Voeg toe aan **Redirect URLs**:
   - `https://turkspot.app/**`
   - `https://kulmetehan.github.io/turkish-diaspora-app/**` (voor GitHub Pages)
4. Ga naar **General** → **Site Name**
5. Stel **Site Name** in op: `Turkspot` (dit wordt getoond tijdens OAuth flow in plaats van de Supabase project URL)
6. Sla op

**Belangrijk**: De Site URL bepaalt waar Supabase gebruikers naartoe redirect na OAuth login. Als dit niet correct is ingesteld, kunnen gebruikers naar het verkeerde domein worden gestuurd.

### 3. Account Linking Inschakelen (BELANGRIJK voor account merging)

Voor automatische account merging moet je Account Linking inschakelen in Supabase:

1. Ga naar Supabase Dashboard → Authentication → Settings
2. Scroll naar "Account Linking" sectie
3. Schakel "Enable account linking" in
4. Configureer:
   - **Link accounts with the same email**: ✅ Ingeschakeld
   - **Require email verification**: ✅ Aanbevolen (maar niet verplicht)
5. Sla op

**Belangrijk**: Met Account Linking ingeschakeld, zal Supabase automatisch accounts linken als:
- Beide accounts hetzelfde email adres hebben
- Het email adres is geverifieerd in beide accounts (als email verification vereist is)
- De gebruiker inlogt met een OAuth provider (Google) en er al een account bestaat met hetzelfde email

## Google Cloud Console Configuratie

### 1. OAuth Client ID Configureren

De volgende configuratie is al ingesteld:

- **Client ID**: `11401442652-j4q4hi5cr8pmhoijh0elh745a38cmjcd.apps.googleusercontent.com`
- **Authorized JavaScript origins**: 
  - `https://kulmetehan.github.io` (GitHub Pages)
  - `https://turkspot.app` (Production domain - **TOEVOEGEN**)
- **Authorized redirect URIs**: `https://shkzerlxzuzourbxujwx.supabase.co/auth/v1/callback`

**⚠️ BELANGRIJK: Voeg turkspot.app toe aan Authorized JavaScript origins**

1. Ga naar [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Open je OAuth 2.0 Client ID (`11401442652-j4q4hi5cr8pmhoijh0elh745a38cmjcd.apps.googleusercontent.com`)
3. Voeg toe aan **Authorized JavaScript origins**:
   - `https://turkspot.app`
4. Sla op

Dit zorgt ervoor dat OAuth redirects correct werken op het productie domein.

### 2. Branding Configureren (BELANGRIJK voor gebruikersvertrouwen)

Volgens de [Supabase documentatie](https://supabase.com/docs/guides/auth/social-login/auth-google) zijn er twee manieren om branding te verbeteren:

#### Optie A: Brand Verification in Google Auth Platform (Aanbevolen)

Dit zorgt ervoor dat "Turkspot" en je logo worden getoond in plaats van de Supabase project URL tijdens de OAuth flow.

1. Ga naar [Google Auth Platform Console](https://console.cloud.google.com/apis/credentials/consent)
2. Selecteer je project
3. Ga naar **Branding** sectie
4. Upload je logo (moet voldoen aan Google's vereisten)
5. Vul in:
   - **Application name**: `Turkspot`
   - **Support email**: Je support email adres
   - **Application home page**: `https://turkspot.app`
   - **Privacy policy URL**: `https://turkspot.app/#/privacy` (BELANGRIJK: gebruik hash router format)
   - **Terms of service URL**: `https://turkspot.app/#/terms` (BELANGRIJK: gebruik hash router format)
6. Sla op en wacht op verificatie (kan enkele werkdagen duren)

**Let op**: Brand verification is niet automatisch en kan enkele werkdagen duren voordat Google het verifieert.

#### Optie B: Custom Domain voor Supabase (Geavanceerd, Optioneel)

Als je een custom domain instelt voor Supabase (bijv. `auth.turkspot.app`), zien gebruikers dit in plaats van `<project-id>.supabase.co`.

**Voordelen**:
- Gebruikers zien een duidelijk verband met je website
- Verbetert gebruikersvertrouwen
- Minder gevoelig voor phishing pogingen

**Nadelen**:
- Vereist DNS configuratie
- Vereist SSL certificaat setup
- Meer complexe setup

**Setup** (als je dit wilt doen):
1. Configureer een subdomain (bijv. `auth.turkspot.app`) in je DNS
2. Stel dit in als custom domain in Supabase Dashboard → Settings → Custom Domains
3. Volg Supabase's instructies voor SSL certificaat setup

**Aanbeveling**: Start met **Optie A** (Brand Verification). Dit is eenvoudiger en geeft al veel verbetering. Optie B is optioneel voor later.

## Account Merging Flow

### Automatische Merging (met Account Linking ingeschakeld)

1. Gebruiker heeft account met email `wwwlamarkanl@gmail.com` (email/wachtwoord)
2. Gebruiker logt in met Google account met hetzelfde email
3. Supabase detecteert dat beide accounts hetzelfde email hebben
4. Supabase linkt automatisch de Google identity aan het bestaande account
5. Gebruiker kan nu inloggen met beide methoden

### Handmatige Merging (zonder Account Linking)

Als Account Linking niet is ingeschakeld:
- Gebruiker moet eerst inloggen met email/wachtwoord
- Dan kan de gebruiker Google account linken via account settings (toekomstige feature)

## Testen

1. Test Google login flow:
   - Ga naar `/auth` pagina
   - Klik op "Google" button
   - Volg OAuth flow
   - Controleer dat je ingelogd bent

2. Test account merging:
   - Maak account met email/wachtwoord (bijv. `wwwlamarkanl@gmail.com`)
   - Log uit
   - Log in met Google met hetzelfde email adres
   - Controleer dat je hetzelfde account gebruikt (zelfde user_id, activiteit, etc.)

3. Test op verschillende plekken:
   - Account pagina (`/account`) - Google login beschikbaar voor niet-ingelogde gebruikers
   - Auth pagina (`/auth`) - Google login beschikbaar naast email/wachtwoord forms

## Environment Variables

Voor correcte OAuth redirects moet je `VITE_FRONTEND_URL` instellen:

### Production (Render)
```bash
VITE_FRONTEND_URL=https://turkspot.app
```

### Development (Local)
```bash
# Optioneel - gebruikt automatisch window.location.origin als niet gezet
VITE_FRONTEND_URL=http://localhost:5173
```

**Waarom nodig?** De OAuth redirect URL moet naar het juiste domein wijzen (`turkspot.app`), niet naar `kulmetehan.github.io` of `localhost`. Als `VITE_FRONTEND_URL` niet is ingesteld, gebruikt de app `window.location.origin` wat kan leiden tot verkeerde redirects.

## Troubleshooting

### Google login werkt niet
- Controleer dat Google OAuth provider is ingeschakeld in Supabase Dashboard
- Controleer dat Client ID en Secret correct zijn ingevuld
- Controleer dat redirect URI correct is geconfigureerd in Google Cloud Console
- Controleer dat `VITE_FRONTEND_URL` is ingesteld op het juiste domein (`https://turkspot.app`)
- Controleer dat Site URL in Supabase is ingesteld op `https://turkspot.app`

### Supabase toont project URL in plaats van "Turkspot.app" tijdens OAuth
- **Oplossing 1 (Snel)**: Stel **Site Name** in op `Turkspot` in Supabase Dashboard → Authentication → General
  - Dit helpt, maar gebruikers zien nog steeds de Supabase project URL in sommige schermen
  
- **Oplossing 2 (Aanbevolen)**: Configureer Brand Verification in Google Auth Platform
  1. Ga naar [Google Auth Platform Console](https://console.cloud.google.com/apis/credentials/consent)
  2. Ga naar **Branding** sectie
  3. Upload logo en vul applicatie naam in (`Turkspot`)
  4. Wacht op verificatie (kan enkele werkdagen duren)
  - Dit zorgt ervoor dat "Turkspot" en je logo worden getoond tijdens de hele OAuth flow
  
- **Oplossing 3 (Geavanceerd)**: Stel custom domain in voor Supabase (`auth.turkspot.app`)
  - Vereist DNS en SSL configuratie
  - Zie bovenstaande documentatie voor details

### Gebruiker komt uitgelogd na Google login
- Controleer dat OAuth callback correct wordt afgehandeld (check browser console)
- Controleer dat `useUserAuth` hook de session correct set
- Controleer Supabase auth logs in dashboard
- Zorg dat redirect URL correct is (moet naar `turkspot.app` wijzen, niet `kulmetehan.github.io`)

### Redirect gaat naar verkeerd domein (kulmetehan.github.io)
- **Oplossing**: Stel `VITE_FRONTEND_URL=https://turkspot.app` in tijdens build
- Voeg `https://turkspot.app` toe aan Authorized JavaScript origins in Google Cloud Console
- Rebuild de frontend na het instellen van de environment variable

### Account merging werkt niet
- Controleer dat Account Linking is ingeschakeld in Supabase Dashboard
- Controleer dat beide accounts hetzelfde email adres hebben
- Controleer dat email is geverifieerd in beide accounts (als email verification vereist is)

### OAuth callback werkt niet
- Controleer dat redirect URL correct is geconfigureerd (`VITE_FRONTEND_URL`)
- Controleer browser console voor errors
- Controleer Supabase auth logs in dashboard
- Zorg dat de hash correct wordt afgehandeld (check `useUserAuth` hook)

## Toekomstige Verbeteringen

- [ ] Apple Sign In toevoegen (vereist Apple Developer Account - €99/jaar)
- [ ] Account linking UI in account settings (om handmatig accounts te linken)
- [ ] Account unlinking functionaliteit
- [ ] Meerdere OAuth providers per account ondersteunen

