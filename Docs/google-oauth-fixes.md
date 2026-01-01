# Google OAuth Fixes - 29 December 2025

## Problemen Geïdentificeerd en Opgelost

### 1. ✅ Redirect URL gebruikt verkeerd domein
**Probleem**: OAuth redirect ging naar `kulmetehan.github.io` in plaats van `turkspot.app`

**Oplossing**:
- `getFrontendBaseUrl()` functie toegevoegd aan `Frontend/src/lib/api.ts`
- Gebruikt `VITE_FRONTEND_URL` environment variable als die is ingesteld
- Val terug op `window.location.origin` voor development
- `VITE_FRONTEND_URL` toegevoegd aan build script met default `https://turkspot.app`

### 2. ✅ OAuth callback conflict tussen useUserAuth en UserAuthPage
**Probleem**: Beide handlers probeerden de callback af te handelen, wat tot conflicten leidde

**Oplossing**:
- `useUserAuth` hook handelt session setting af
- `UserAuthPage` gebruikt `onAuthStateChange` event om OAuth login te detecteren
- Return URL wordt opgeslagen in `sessionStorage` voor OAuth callbacks
- `useUserAuth` slaat return URL op voordat hash wordt opgeschoond

### 3. ✅ Google login alleen beschikbaar op /auth
**Probleem**: Google login was alleen op `/auth` pagina, niet op andere plekken

**Oplossing**:
- `LoginPrompt` component bijgewerkt met Google login button
- `LoginModal` component bijgewerkt met Google login button
- `AccountLoginSection` al bijgewerkt (was al gedaan)

### 4. ✅ Geen Google optie na redirect
**Probleem**: Na OAuth redirect zag je geen Google login optie meer

**Oplossing**:
- Google login is nu altijd beschikbaar op `/auth` pagina
- OAuth callback handler gebruikt `onAuthStateChange` voor betere detectie
- Return URL wordt correct opgeslagen en opgehaald

## Wijzigingen

### Frontend Files
1. **`Frontend/src/lib/api.ts`**
   - `getFrontendBaseUrl()` functie toegevoegd
   - Gebruikt `VITE_FRONTEND_URL` environment variable

2. **`Frontend/src/components/auth/GoogleLoginButton.tsx`**
   - Gebruikt `getFrontendBaseUrl()` voor correcte redirect URL
   - Slaat return URL op in `sessionStorage` voor OAuth callbacks

3. **`Frontend/src/pages/UserAuthPage.tsx`**
   - OAuth callback handler verbeterd met `onAuthStateChange`
   - Haalt return URL op uit `sessionStorage`
   - Betere error handling en redirect logica

4. **`Frontend/src/hooks/useUserAuth.ts`**
   - Slaat return URL op in `sessionStorage` voor OAuth callbacks
   - Detecteert OAuth callbacks vs recovery links

5. **`Frontend/src/components/auth/LoginPrompt.tsx`**
   - Google login button toegevoegd
   - Betere UX met "Of" divider

6. **`Frontend/src/components/auth/LoginModal.tsx`**
   - Google login button toegevoegd
   - Sluit modal na succesvolle OAuth login

7. **`Frontend/vite-env.d.ts`**
   - `VITE_FRONTEND_URL` type definitie toegevoegd

8. **`Frontend/build.sh`**
   - `VITE_FRONTEND_URL` toegevoegd aan build script
   - Default waarde: `https://turkspot.app`

## Actie Vereist

### 1. Google Cloud Console - Authorized JavaScript Origins
Voeg `https://turkspot.app` toe aan Authorized JavaScript origins:

1. Ga naar [Google Cloud Console](https://console.cloud.google.com/)
2. Navigeer naar **APIs & Services** → **Credentials**
3. Open je OAuth 2.0 Client ID (`11401442652-j4q4hi5cr8pmhoijh0elh745a38cmjcd.apps.googleusercontent.com`)
4. Voeg toe aan **Authorized JavaScript origins**:
   - `https://turkspot.app`
5. Sla op

### 2. Environment Variable - VITE_FRONTEND_URL
Stel `VITE_FRONTEND_URL` in tijdens build:

**Render (Production)**:
```bash
VITE_FRONTEND_URL=https://turkspot.app
```

**Local Development** (optioneel):
```bash
VITE_FRONTEND_URL=http://localhost:5173
```

Als niet ingesteld, gebruikt de app `window.location.origin` (werkt voor localhost, maar kan problemen geven bij cross-domain redirects).

### 3. Supabase Account Linking
Zorg dat Account Linking is ingeschakeld voor automatische account merging:

1. Supabase Dashboard → Authentication → Settings
2. Scroll naar "Account Linking"
3. Schakel "Enable account linking" in
4. Configureer:
   - **Link accounts with the same email**: ✅ Ingeschakeld
   - **Require email verification**: ✅ Aanbevolen

## Testen

Na het implementeren van bovenstaande fixes:

1. **Test Google login flow**:
   - Ga naar `https://turkspot.app/#/auth`
   - Klik op "Google" button
   - Volg OAuth flow
   - Controleer dat je ingelogd bent en naar juiste pagina redirect

2. **Test account merging**:
   - Maak account met email/wachtwoord (bijv. `wwwlamarkanl@gmail.com`)
   - Log uit
   - Log in met Google met hetzelfde email adres
   - Controleer dat je hetzelfde account gebruikt

3. **Test op verschillende plekken**:
   - Account pagina (`/account`) - Google login beschikbaar
   - Login prompts - Google login beschikbaar
   - Login modal - Google login beschikbaar

## Troubleshooting

### Redirect gaat nog steeds naar kulmetehan.github.io
- Controleer dat `VITE_FRONTEND_URL=https://turkspot.app` is ingesteld tijdens build
- Rebuild de frontend na het instellen van de environment variable
- Controleer dat `https://turkspot.app` is toegevoegd aan Google Cloud Console Authorized JavaScript origins

### Gebruiker komt uitgelogd na Google login
- Controleer browser console voor errors
- Controleer Supabase auth logs in dashboard
- Controleer dat OAuth callback correct wordt afgehandeld (check `onAuthStateChange` events)

### Google login optie verschijnt niet
- Controleer dat `GoogleLoginButton` component correct is geïmporteerd
- Controleer browser console voor import errors
- Refresh de pagina (hard refresh: Cmd+Shift+R / Ctrl+Shift+R)


