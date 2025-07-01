import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient
from src.services.database import Database
from src.models.user import User
from src.services.auth_service import get_password_hash

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Use a different database for tests
    test_mongo_uri = "mongodb://mongo:27017/test_db"
    await Database.connect(mongo_uri=test_mongo_uri, db_name="test_db")
    yield
    # Clean up after each test
    try:
        await Database.engine.get_collection(User).drop()
    except Exception:
        pass  # Ignore errors during cleanup
    await Database.close()

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    from src.main import app # Import app inside the fixture

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        data={
            "email": "test@example.com",
            "nom": "Test",
            "prenom": "User",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    assert "Inscription réussie" in response.text

    user = await Database.engine.find_one(User, User.email == "test@example.com")
    assert user is not None
    assert user.nom == "Test"
    assert user.prenom == "User"
    assert user.roles == ["user"]

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient):
    # Register a user first
    hashed_password = get_password_hash("testpassword")
    user = User(email="login@example.com", nom="Login", prenom="User", pwd=hashed_password)
    await Database.engine.save(user)

    response = await client.post(
        "/auth/token",
        data={
            "username": "login@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "token_type" in response.json()

@pytest.mark.asyncio
async def test_access_superadmin_dashboard_unauthorized(client: AsyncClient):
    response = await client.get("/superadmin/dashboard")
    assert response.status_code == 401 # Unauthorized

@pytest.mark.asyncio
async def test_access_superadmin_dashboard_authorized(client: AsyncClient):
    # Register a superadmin user
    hashed_password = get_password_hash("superadminpassword")
    superadmin_user = User(email="superadmin@example.com", nom="Super", prenom="Admin", pwd=hashed_password, roles=["superadmin"])
    await Database.engine.save(superadmin_user)

    # Get access token for superadmin
    token_response = await client.post(
        "/auth/token",
        data={
            "username": "superadmin@example.com",
            "password": "superadminpassword"
        }
    )
    access_token = token_response.json()["access_token"]

    response = await client.get(
        "/superadmin/dashboard",
        headers={
            "Authorization": f"Bearer {access_token}"
        }
    )
    assert response.status_code == 200
    assert "Tableau de bord Superadmin" in response.text # Corrected text to match the actual template