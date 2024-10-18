# My Flask App

This Flask application fetches and displays COVID-19 data for selected countries and currency exchange rates for the last month.

## Features

1. **COVID-19 Data Fetching and Display:**
   - Fetches the latest COVID-19 data for selected countries (Poland, Germany, Russia, China, USA, France, United Kingdom) using the [COVID-API](https://covid-api.com/api/).
   - Displays the data in a table format, showing active cases, total cases, and total deaths for each country.
   - Stores the fetched data in a SQLite database to avoid redundant API calls.

2. **Currency Exchange Rates:**
   - Fetches the top 10 currency exchange rates from the [NBP API](http://api.nbp.pl/api/exchangerates/tables/A?format=json).
   - Fetches historical exchange rates for the last month for each of the top 10 currencies.
   - Displays the exchange rates in a table and generates plots for the historical data.
   - Stores the fetched data in a SQLite database to avoid redundant API calls.

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-username/your-repo.git
   cd your-repo