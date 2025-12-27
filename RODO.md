# RODO i Bezpieczenstwo - Szczegolowa Dokumentacja

## 1. Endpoint do realizacji prawa do usuniecia danych (Art. 17 RODO)

**Priorytet:** Niski (obecnie mozna realizowac recznie przez panel admina)

**Dlaczego warto dodac:**

- Art. 17 RODO gwarantuje osobom prawo do zadania usuniecia ich danych osobowych
- Obecnie administrator musi recznie usuwac dane na zadanie uzytkownika
- Automatyczny endpoint pozwolilby uzytkownikom samodzielnie usunac swoje dane
- Zmniejsza obciazenie administracyjne i ryzyko bledu ludzkiego

**Proponowana implementacja:**

- Endpoint `/zgloszenie/<token>/usun/` dostepny dla uzytkownika
- Potwierdzenie emailem przed usunieciem
- Logowanie operacji usuniecia dla celow audytowych
- Usuniecie danych wrazliwych (Dane_Dodatkowe) z zachowaniem anonimizowanego
  rekordu zgloszenia dla celow statystycznych

---

## 2. Migracja bazy danych SQLite -> PostgreSQL z szyfrowaniem

**Priorytet:** Niski (SQLite wystarczajacy dla malej skali)

**Dlaczego warto rozwazyc:**

- SQLite nie wspiera szyfrowania na poziomie bazy danych
- PostgreSQL oferuje Transparent Data Encryption (TDE) i lepsze zarzadzanie
  uprawnieniami
- Lepsza skalowalnosc przy wzroscie liczby uzytkownikow
- Mozliwosc replikacji i backupow przyrostowych
- Wymagane przy wdrozeniu na wieksza skale lub w srodowisku produkcyjnym
  z wieloma uzytkownikami

**Kiedy wdrozyc:**

- Gdy liczba zgloszen przekroczy ~1000 rocznie
- Przy wdrozeniu na serwer produkcyjny z wieloma administratorami
- Gdy wymagana bedzie wysoka dostepnosc (HA)

**Uwagi:**

- Wymaga zmiany infrastruktury hostingowej
- Konieczna migracja istniejacych danych
- Dodatkowe koszty utrzymania serwera bazy danych

---

## 3. Rotacja klucza szyfrowania (Key Rotation)

**Priorytet:** Sredni (wazne dla dlugoterminowego bezpieczenstwa)

**Dlaczego warto dodac:**

- Obecny klucz Fernet jest statyczny - kompromitacja = dostep do wszystkich
  danych
- Regularna rotacja kluczy minimalizuje ryzyko wycieku
- Zgodnosc z najlepszymi praktykami bezpieczenstwa (NIST, ISO 27001)

**Proponowana implementacja:**

- Wsparcie dla wielu kluczy (aktywny + poprzednie do odczytu)
- Komenda Django do re-szyfrowania danych nowym kluczem
- Automatyczne usuwanie starych kluczy po re-szyfrowaniu

---

## 4. Dwuskladnikowe uwierzytelnianie (2FA) dla administratorow

**Priorytet:** Sredni

**Dlaczego warto dodac:**

- Administratorzy maja dostep do danych wrazliwych (PESEL, dokumenty)
- Samo haslo nie jest wystarczajacym zabezpieczeniem
- 2FA znaczaco zmniejsza ryzyko nieautoryzowanego dostepu

**Proponowana implementacja:**

- Biblioteka `django-otp` lub `django-two-factor-auth`
- TOTP (aplikacje typu Google Authenticator)
- Wymagane dla wszystkich uzytkownikow z dostepem do panelu admina

---

## Uwagi ogolne

- Zadania oznaczone jako "Niski priorytet" moga byc realizowane w miare
  dostepnosci zasobow
- Przed wdrozeniem zadan zwiazanych z RODO zalecana konsultacja z prawnikiem
- Dane kontaktowe administratora danych w klauzuli RODO wymagaja uzupelnienia
  (plik: `rejs/templates/rejs/rodo_info.html`)
