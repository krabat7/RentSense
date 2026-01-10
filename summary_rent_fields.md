# Анализ полей для аренды vs продажа

## Результаты анализа объявления об аренде (ID: 311739319)

### ✅ Поля, которые уже парсятся и работают:
- Основные: cianId, dealType, category, description
- Цена: price (из bargainTerms.price для аренды)
- Площади: totalArea, livingArea, kitchenArea, roomsCount
- Здание: floorsCount, floorNumber, parking_type
- Интерьер: repairType, balconies, loggias, WC, windows_view
- Гео: coordinates, metro, address, travel_time
- Агент: agent_name, views_count

### ❌ Поля для аренды, которые НЕ парсятся (но есть в данных):

1. **paymentPeriod** (monthly/daily) - период оплаты
2. **leaseTermType** (longTerm/shortTerm) - тип аренды
3. **deposit** (80000) - залог
4. **prepayMonths** (1) - предоплата в месяцах
5. **utilitiesIncluded** (True/False) - включены ли коммунальные
6. **clientFee** (70) - комиссия клиента
7. **agentFee** (0) - комиссия агента

### ⚠️ Поля для продажи, которых нет в аренде:
- mortgageAllowed - может быть None для аренды (это нормально)
- saleType - может быть None для аренды (это нормально)

### 📋 Рекомендации:

1. Добавить поля для аренды в таблицу `offers_details`:
   - payment_period (String)
   - lease_term_type (String)
   - deposit (DECIMAL)
   - prepay_months (Integer)
   - utilities_included (Boolean)
   - client_fee (Integer)
   - agent_fee (Integer)

2. Обновить `pagecheck.py` для парсинга этих полей из `bargainTerms`

3. Поля для продажи (mortgageAllowed, saleType) оставить как есть - они будут None для аренды

