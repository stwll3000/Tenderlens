.PHONY: install dashboard analyze test scrape enrich load help

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

dashboard: ## Запустить Streamlit-дашборд
	streamlit run dashboard/app.py

analyze: ## Запустить аудит-анализ (без БД)
	python analysis/run_audit_analysis.py

test: ## Запустить тесты
	pytest tests/ -v

scrape: ## Собрать лоты с zakupki.gov.ru (3 региона, 500 лотов)
	python scraper/collect_multi_regions.py

enrich: ## Обогатить 100 лотов детальной информацией
	python scraper/enrich_100_lots.py

load: ## Загрузить данные в БД (нужен .env с DATABASE_URL)
	python db/init_database.py

lint: ## Проверка кода (ruff)
	ruff check analytics/ db/ scraper/ dashboard/
