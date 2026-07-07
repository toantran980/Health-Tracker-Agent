from api.mongo_store import MongoStore
from datetime import datetime

store = MongoStore.from_env()
# Only run if MongoDB for localhost is enabled

# Insert test users
u1 = store.save_user({
    "user_id": "user_1",
    "name": "Test User 1",
    "email": "user1@example.com"
})
u2 = store.save_user({
    "user_id": "user_2",
    "name": "Test User 2",
    "email": "user2@example.com"
})
u3 = store.save_user({
    "user_id": "user_3",
    "name": "Test User 3",
    "email": "user3@example.com"
})
print("Inserted users:", u1, u2, u3)

# Insert test daily logs
d1 = store._db["daily_logs"].insert_one({
    "user_id": "user_1",
    "date": "2024-04-25",
    "log": "Sample log 1"
})
d2 = store._db["daily_logs"].insert_one({
    "user_id": "user_2",
    "date": "2024-04-25",
    "log": "Sample log 2"
})
d3 = store._db["daily_logs"].insert_one({
    "user_id": "user_3",
    "date": "2024-04-25",
    "log": "Sample log 3"
})
print("Inserted daily_logs:", d1.inserted_id, d2.inserted_id, d3.inserted_id)

# Insert test activities
a1 = store.save_activity({
    "activity_id": "test_activity_1",
    "user_id": "user_1",
    "type": "test_activity",
    "created_at": datetime.now()
})
a2 = store.save_activity({
    "activity_id": "test_activity_2",
    "user_id": "user_2",
    "type": "test_activity",
    "created_at": datetime.now()
})
a3 = store.save_activity({
    "activity_id": "test_activity_3",
    "user_id": "user_3",
    "type": "test_activity",
    "created_at": datetime.now()
})
print("Inserted activities:", a1, a2, a3)

# Insert test recommendations
r1 = store.save_recommendation({
    "user_id": "user_1",
    "recommendation": "test_recommendation_1",
    "created_at": datetime.now()
})
r2 = store.save_recommendation({
    "user_id": "user_2",
    "recommendation": "test_recommendation_2",
    "created_at": datetime.now()
})
r3 = store.save_recommendation({
    "user_id": "user_3",
    "recommendation": "test_recommendation_3",
    "created_at": datetime.now()
})
print("Inserted recommendations:", r1, r2, r3)

# Insert test meals
m1 = store.save_meal({
    "meal_id": "test_meal_1",
    "user_id": "user_1",
    "timestamp": datetime.now(),
    "description": "test meal 1"
})
m2 = store.save_meal({
    "meal_id": "test_meal_2",
    "user_id": "user_2",
    "timestamp": datetime.now(),
    "description": "test meal 2"
})
m3 = store.save_meal({
    "meal_id": "test_meal_3",
    "user_id": "user_3",
    "timestamp": datetime.now(),
    "description": "test meal 3"
})
print("Inserted meals:", m1, m2, m3)