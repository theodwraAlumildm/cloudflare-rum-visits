# Cloudflare Analytics Aggregator

Αυτό το script ανακτά στατιστικά στοιχεία επισκεψιμότητας (RUM) από το Cloudflare GraphQL API και τα ομαδοποιεί ανά path.

## Λογική & Στρατηγική

1. Χρονική Διαχείριση (Timezone Alignment)
Επειδή το Cloudflare API λειτουργεί αυστηρά σε UTC, το script μετατρέπει την τοπική ώρα (Europe/Athens) σε UTC για να διασφαλίσει ότι το report καλύπτει ακριβώς το 24ωρο της επιλογής μας.

2. Chunking (Αποφυγή API Limits & Αντιστοίχιση)
Το GraphQL endpoint έχει όριο 10.000 εγγραφές ανά αίτημα. Χωρίζουμε την ημέρα σε 4 εξάωρα για να μην χάνουμε δεδομένα. 

Για να έχουμε το ίδιο αποτέλεσμα με το Cloudflare Dashboard, λαμβάνουμε υπόψην ότι το Dashboard της Cloudflare έχει δύο τρόπους να εμφανίζει τα δεδομένα:

UTC: Η "μητρική" ζώνη της Cloudflare.

Dashboard Local Time: Η ζώνη που έχουμε επιλέξει στις ρυθμίσεις του account.

Η Λογική του Script
Χρησιμοποιεί την Europe/Athens (GMT+3). Το script παίρνει το "χθες" (yesterday) σε τοπική ώρα και το μετατρέπει σε UTC για να ευθυγραμμιστεί με το Dashboard.

Πώς θα είναι τα Timestamps στο Dashboard;
Αν θέλουμε να βλέπουμε στο Cloudflare Dashboard ακριβώς το ίδιο "χθες" που υπολογίζει το script, πρέπει να προσέξουμε τα εξής:

1. Η μορφή των Timestamps
Το GraphQL της Cloudflare απαιτεί ISO 8601 string. Το script παράγει:
YYYY-MM-DDTHH:MM:SSZ

Στο Dashboard: Όταν επιλέγουμε "Yesterday" (Χθες), η Cloudflare κάνει αυτόματα το query για το διάστημα 00:00:00 έως 23:59:59 της τοπικής μας ώρας.

2. Τα "Chunks" (Τα 6ωρα)
Για να συμπίπτουν οι ώρες με το Dashboard, τα timestamps που παράγει η συνάρτησή local_to_utc_iso πρέπει να αντιστοιχούν σε αυτά:

**Πίνακας αντιστοίχισης ωρών:**

| Chunk (Τοπική Αθήνας) | Script Input (Ώρες) | Cloudflare Dashboard (UTC) |
| :--- | :--- | :--- |
| 00:00 - 06:00 | 0,0,0 έως 6,0,0 | 21:00 (προηγ.) - 03:00 (τρέχ.) |
| 06:00 - 12:00 | 6,0,0 έως 12,0,0 | 03:00 - 09:00 |
| 12:00 - 18:00 | 12,0,0 έως 18,0,0 | 09:00 - 15:00 |
| 18:00 - 23:59 | 18,0,0 έως 23,59,59 | 15:00 - 21:00 |

ΠΑΡΑΔΕΙΓΜΑ ΑΠΟ 01/06 
DASHBOARD
JUN 1, 00:00-JUN 1, 23:59 (EEST)
Path contains/greece
8.41k

CONSOLE (με τα παραπάνω chunks)
/greece: 8414





### 3. Διαχείριση & Εκτύπωση Επισκέψεων
Η διαδικασία συλλογής των δεδομένων ακολουθεί αυτή τη λογική:
- **Ανάκτηση:** Για κάθε εξάωρο, πραγματοποιείται POST request στο API.
- **Επεξεργασία (Parsing):** Το script απομονώνει το πρώτο segment του URL (π.χ. `/en/home` γίνεται `/en`).
- **Aggregation:** Χρησιμοποιείται η δομή `defaultdict(int)` της Python. Κάθε φορά που συναντάται ένα path (π.χ. `/en`), το script προσθέτει τις επισκέψεις στο υπάρχον σύνολο του συγκεκριμένου key, χωρίς να χρειάζεται έλεγχο ύπαρξης.
- **Σύνοψη:** Τέλος, το script ταξινομεί αλφαβητικά τα paths (`sorted`) και εκτυπώνει το σύνολο των επισκέψεων ανά path, καθώς και το γενικό σύνολο (`total_path_visits`).

### 4. Adaptive Sampling
Χρησιμοποιούμε το `rumPageloadEventsAdaptiveGroups`. Είναι απαραίτητο για sites με μεγάλο traffic, καθώς επιστρέφει ομαδοποιημένα δεδομένα, αποτρέποντας τα time-outs.

## Ρύθμιση (.env)
Για να τρέξει το script, χρειάζεται ένα αρχείο `.env` με:
- `CLOUDFLARE_API_TOKEN`: Το API Token σας.
- `CLOUDFLARE_ACCOUNT_TAG`: Το Account Tag της Cloudflare.
