"""Ingest meteorological documents into pgvector knowledge base.

Generates embeddings for ~23 meteorological documents covering laws, rules,
patterns, and activity-specific guides, then inserts them into the
knowledge_base table in PostgreSQL.

Usage:
    python scripts/ingest_knowledge.py
    python scripts/ingest_knowledge.py --reset
    python scripts/ingest_knowledge.py --dry-run
"""

import argparse
import logging
import os
from dataclasses import dataclass
from typing import List

import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@dataclass
class KnowledgeDoc:
    """Single meteorological document to ingest."""

    title: str
    content: str
    category: str


DOCUMENTS: List[KnowledgeDoc] = [
    # === LAWS (3) ===
    KnowledgeDoc(
        title="Magnus Law: Humidity and Precipitation",
        content=(
            "The Magnus formula describes the relationship between temperature, "
            "dew point, and relative humidity. When relative humidity exceeds 80% "
            "and atmospheric pressure drops below 1010 hPa, the air approaches "
            "saturation and precipitation becomes highly likely. This occurs because "
            "cooling air reduces its capacity to hold water vapor, forcing condensation "
            "into cloud droplets and eventually rain. The dew point is the temperature "
            "at which air becomes saturated (100% relative humidity) at constant pressure."
        ),
        category="law",
    ),
    KnowledgeDoc(
        title="Clausius-Clapeyron Relation: Temperature and Vapor Capacity",
        content=(
            "The Clausius-Clapeyron equation states that the atmosphere's water vapor "
            "holding capacity increases by approximately 7% for each 1 degree Celsius "
            "increase in temperature. This means warmer air can hold significantly more "
            "moisture before reaching saturation. Conversely, cooling air by even a few "
            "degrees can dramatically increase relative humidity and trigger condensation. "
            "This principle explains why temperature drops at night often lead to dew, "
            "fog, or frost formation."
        ),
        category="law",
    ),
    KnowledgeDoc(
        title="Magnus Formula: Dew Point Calculation",
        content=(
            "The Magnus formula calculates dew point temperature from air temperature "
            "and relative humidity: Td = (b * alpha) / (a - alpha), where "
            "alpha = (a * RH / (100 + RH)) + ln(RH/100), with constants a=17.27 "
            "and b=237.7 degrees Celsius. When the dew point is close to the current "
            "temperature (within 2-3 degrees), fog or low clouds are likely. A large "
            "gap between temperature and dew point indicates dry air and low precipitation "
            "probability."
        ),
        category="formula",
    ),
    # === RULES (9) ===
    KnowledgeDoc(
        title="Low Pressure System: Instability Indicator",
        content=(
            "Atmospheric pressure below 1013 hPa (standard sea level pressure) indicates "
            "a low pressure system. Low pressure is associated with rising air, cloud "
            "formation, and potentially unstable weather conditions including rain, "
            "wind, and storms. The lower the pressure, the more intense the system. "
            "Pressure below 1000 hPa typically indicates a strong low pressure system "
            "with significant weather impacts."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="High Pressure System: Stability Indicator",
        content=(
            "Atmospheric pressure above 1020 hPa indicates a high pressure system. "
            "High pressure is associated with sinking air, clear skies, and stable "
            "weather conditions. During high pressure periods, precipitation is unlikely, "
            "winds are generally light, and visibility is good. In winter, high pressure "
            "can bring cold, clear nights with frost risk due to radiative cooling."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="High Humidity with Falling Pressure: Rain Likely",
        content=(
            "When relative humidity exceeds 80% and atmospheric pressure is falling, "
            "rain is highly probable within the next 6-12 hours. This combination "
            "indicates that moist air is being lifted and cooled, reaching saturation. "
            "The falling pressure signals an approaching weather front or low pressure "
            "system. The faster the pressure drop, the sooner and more intense the "
            "precipitation is likely to be."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="Low Humidity: Dry Air Conditions",
        content=(
            "Relative humidity below 30% indicates very dry air conditions. Under "
            "these conditions, precipitation is extremely unlikely, evaporation rates "
            "are high, and fire risk increases significantly. Low humidity combined "
            "with high temperatures creates uncomfortable heat as the body's cooling "
            "mechanism (sweating) becomes less effective. In winter, low humidity "
            "can cause static electricity and dry skin."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="High Wind Speed: Windy Conditions",
        content=(
            "Wind speed exceeding 40 km/h indicates windy conditions that can affect "
            "outdoor activities, driving, and maritime operations. Sustained winds "
            "above 40 km/h can cause tree branches to sway, make cycling difficult, "
            "and create hazardous driving conditions for high-profile vehicles. Wind "
            "gusts are typically 1.3-1.5 times the sustained wind speed. Wind chill "
            "effect becomes significant at these speeds, making the perceived "
            "temperature several degrees lower than the actual temperature."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="Low Temperature: Cold and Frost Risk",
        content=(
            "Temperature below 5 degrees Celsius indicates cold conditions requiring "
            "warm clothing. Below 0 degrees Celsius, frost and ice formation is possible, "
            "creating hazardous road conditions. The risk of frost is highest on clear, "
            "calm nights when radiative cooling is maximized. Wind can prevent frost "
            "by mixing warmer air from above, while calm conditions allow cold air to "
            "settle near the ground. Dew point temperature is a better frost indicator "
            "than air temperature: if dew point is below 0 degrees Celsius, frost is likely."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="High Temperature: Extreme Heat Conditions",
        content=(
            "Temperature above 35 degrees Celsius indicates extreme heat conditions. "
            "Heat index (apparent temperature) can be significantly higher when combined "
            "with high humidity, as the body's ability to cool through evaporation is "
            "reduced. Heat exhaustion becomes a risk above 32 degrees Celsius with high "
            "humidity. Hydration, shade, and reduced physical activity are essential. "
            "Urban heat island effect can make city temperatures 3-5 degrees higher "
            "than surrounding rural areas."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="High Cloud Cover: Overcast Conditions",
        content=(
            "Cloud cover above 80% indicates overcast skies with limited sunlight. "
            "High cloud cover combined with high humidity and falling pressure strongly "
            "suggests imminent precipitation. Different cloud types indicate different "
            "conditions: nimbostratus clouds bring steady rain, cumulonimbus clouds "
            "indicate thunderstorms, and stratus clouds produce light drizzle. Cloud "
            "cover also affects temperature: overcast nights are warmer than clear "
            "nights due to reduced radiative cooling."
        ),
        category="rule",
    ),
    KnowledgeDoc(
        title="Low Cloud Cover: Clear Sky Conditions",
        content=(
            "Cloud cover below 20% indicates clear skies with abundant sunlight. "
            "Clear skies during the day lead to strong solar heating and higher "
            "temperatures. Clear skies at night lead to rapid radiative cooling and "
            "potential frost formation in cold conditions. UV radiation is highest "
            "under clear skies. Clear conditions combined with high pressure indicate "
            "stable, pleasant weather. Clear skies with low humidity indicate dry, "
            "comfortable conditions."
        ),
        category="rule",
    ),
    # === PATTERNS (5) ===
    KnowledgeDoc(
        title="Rapid Pressure Drop: Approaching Storm Front",
        content=(
            "A rapid drop in atmospheric pressure (more than 3 hPa in 3 hours) indicates "
            "an approaching storm front or intense low pressure system. This pattern "
            "typically precedes severe weather including heavy rain, strong winds, and "
            "possible thunderstorms by 6-12 hours. The faster the pressure drop, the "
            "more intense the approaching weather system. A pressure drop of 5+ hPa "
            "in 3 hours often indicates a rapidly developing storm that may bring "
            "dangerous conditions."
        ),
        category="pattern",
    ),
    KnowledgeDoc(
        title="Stable Pressure with High Humidity: Morning Fog Risk",
        content=(
            "When atmospheric pressure remains stable and relative humidity is above "
            "90% during the evening, morning fog is likely to form overnight. This "
            "occurs because radiative cooling during clear, calm nights reduces air "
            "temperature to the dew point, causing water vapor to condense into "
            "suspended droplets near the ground. Fog typically dissipates within 1-3 "
            "hours after sunrise as the sun warms the air. Radiation fog is most "
            "common in valleys and low-lying areas where cold air pools."
        ),
        category="pattern",
    ),
    KnowledgeDoc(
        title="Cirrus Clouds with Falling Pressure: Weather Change in 24-48 Hours",
        content=(
            "The appearance of high, wispy cirrus clouds combined with gradually "
            "falling atmospheric pressure indicates an approaching warm front and "
            "weather change within 24-48 hours. Cirrus clouds form at high altitudes "
            "(6-12 km) and are the first visible sign of an approaching weather system. "
            "The classic progression is: cirrus clouds appear, pressure begins to fall, "
            "clouds thicken to cirrostratus then altostratus, and finally nimbostratus "
            "clouds bring precipitation."
        ),
        category="pattern",
    ),
    KnowledgeDoc(
        title="Gusty Wind with Falling Pressure: Imminent Storm",
        content=(
            "Increasing wind gusts combined with falling atmospheric pressure indicate "
            "an imminent storm, often within 2-6 hours. This pattern occurs as the "
            "pressure gradient between the approaching low pressure system and surrounding "
            "areas intensifies, driving stronger winds. Gusty, shifting wind directions "
            "suggest turbulent atmospheric conditions typical of thunderstorms and squall "
            "lines. When wind gusts exceed 60 km/h with falling pressure, seek shelter "
            "as severe weather is likely approaching."
        ),
        category="pattern",
    ),
    KnowledgeDoc(
        title="High Pressure Gradient: Sustained Strong Winds",
        content=(
            "A large difference in atmospheric pressure over a short distance (high "
            "pressure gradient) produces sustained strong winds. On weather maps, this "
            "is indicated by closely spaced isobars. The steeper the pressure gradient, "
            "the stronger the winds. A pressure difference of 10 hPa over 100 km typically "
            "produces winds of 30-40 km/h. A difference of 20+ hPa over 100 km can produce "
            "gale-force winds above 60 km/h. Coastal areas experience amplified wind effects "
            "due to reduced surface friction over water."
        ),
        category="pattern",
    ),
    # === ACTIVITIES (6) ===
    KnowledgeDoc(
        title="Navigation: Calm and Rough Sea Conditions",
        content=(
            "For maritime navigation, wind speed below 15 km/h with stable atmospheric "
            "pressure indicates calm sea conditions suitable for small boats. Wind speed "
            "above 25 km/h creates choppy seas with wave heights of 0.5-1 meter. Wind "
            "above 40 km/h produces rough seas with waves 1-2 meters, hazardous for "
            "small vessels. Wind direction relative to current is critical: wind against "
            "current creates steeper, shorter waves that are more dangerous than wind "
            "with current. Falling pressure with increasing wind indicates deteriorating "
            "conditions and mariners should seek shelter."
        ),
        category="activity",
    ),
    KnowledgeDoc(
        title="Navigation: Coastal Weather Deterioration",
        content=(
            "Coastal weather can deteriorate rapidly when pressure falls below 1010 hPa "
            "combined with increasing wind speed and shifting wind direction. The sea "
            "state responds quickly to wind changes: a wind shift from onshore to offshore "
            "can rapidly change wave patterns. Coastal fog forms when warm, moist air "
            "moves over cooler coastal waters (advection fog). Thunderstorms over water "
            "are particularly dangerous due to lightning risk and sudden wind shifts. "
            "Always monitor pressure trends and wind direction when navigating coastal "
            "waters."
        ),
        category="activity",
    ),
    KnowledgeDoc(
        title="Aviation: Visibility, Wind Shear, and IFR Conditions",
        content=(
            "For aviation, visibility below 5 km with cloud base below 1000 feet indicates "
            "Instrument Flight Rules (IFR) conditions requiring instrument rating. Wind "
            "shear (rapid change in wind speed or direction with altitude) is most "
            "dangerous during takeoff and landing, particularly near thunderstorms and "
            "temperature inversions. Crosswind components above 20 knots challenge most "
            "light aircraft. Low pressure systems bring turbulence, reduced visibility, "
            "and icing risk at altitude. Pressure altitude affects aircraft performance: "
            "high temperature and low pressure reduce engine power and lift."
        ),
        category="activity",
    ),
    KnowledgeDoc(
        title="Aviation: Low Clouds and Fog",
        content=(
            "Low cloud cover (ceiling below 500 feet) and fog are the primary causes of "
            "flight delays and diversions. Radiation fog forms on clear, calm nights and "
            "typically burns off within 1-3 hours after sunrise. Advection fog forms when "
            "warm moist air moves over cooler surfaces and can persist all day. Cloud "
            "ceiling trends are more important than current conditions: a falling ceiling "
            "indicates deteriorating conditions even if current visibility is adequate. "
            "Dew point within 2 degrees of temperature indicates high fog probability."
        ),
        category="activity",
    ),
    KnowledgeDoc(
        title="Mountain: High Altitude Wind and Ice Risk",
        content=(
            "Mountain weather is more extreme than valley conditions. Wind speed at "
            "altitude is typically 1.5-2 times valley wind speed due to reduced surface "
            "friction and funnelling effects. Wind above 50 km/h at altitude creates "
            "dangerous conditions for exposed ridges and summits. Temperature decreases "
            "approximately 6.5 degrees Celsius per 1000 meters of elevation gain. "
            "Below 0 degrees Celsius at altitude, ice formation on rocks and trails "
            "creates extreme fall risk. Mountain weather changes rapidly: clear conditions "
            "can deteriorate to whiteout within minutes when a front passes."
        ),
        category="activity",
    ),
    KnowledgeDoc(
        title="Motorcycling and Cycling: Rain and Wind Danger",
        content=(
            "For motorcycling and cycling, rain combined with wind above 20 km/h creates "
            "dangerous riding conditions. Wet roads reduce tire grip by 30-50%, increasing "
            "braking distances significantly. Crosswinds above 30 km/h can destabilize "
            "two-wheeled vehicles, especially when exiting wind shelters or passing large "
            "vehicles. Temperature below 5 degrees Celsius with rain creates ice risk on "
            "bridges and shaded sections. Wind chill at riding speeds makes perceived "
            "temperature 10-15 degrees lower than ambient, requiring appropriate protective "
            "gear to prevent hypothermia."
        ),
        category="activity",
    ),
]


def get_db_url() -> str:
    """Get database URL from environment or use docker-compose defaults."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://weather:weather@localhost:5432/weather_agent",
    )


def load_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    """Load the sentence-transformers embedding model."""
    logger.info("Loading embedding model: %s", model_name)
    model = SentenceTransformer(model_name)
    logger.info("Model loaded: %d dimensions", model.get_sentence_embedding_dimension())
    return model


def generate_embeddings(
    model: SentenceTransformer,
    documents: List[KnowledgeDoc],
) -> List[tuple]:
    """Generate embeddings for all documents.

    Returns list of (title, content, category, embedding) tuples.
    """
    texts = [f"{doc.title}. {doc.content}" for doc in documents]

    logger.info("Generating embeddings for %d documents...", len(documents))
    embeddings = model.encode(texts, show_progress_bar=True)

    results = []
    for doc, embedding in zip(documents, embeddings):
        results.append((doc.title, doc.content, doc.category, embedding.tolist()))

    return results


def connect_to_db(db_url: str) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL and register pgvector extension."""
    logger.info("Connecting to database...")
    conn = psycopg2.connect(db_url)
    register_vector(conn)
    logger.info("Connected and pgvector registered")
    return conn


def insert_documents(
    conn: psycopg2.extensions.connection,
    documents: List[tuple],
    reset: bool = False,
) -> int:
    """Insert documents into knowledge_base table.

    Args:
        conn: PostgreSQL connection.
        documents: List of (title, content, category, embedding) tuples.
        reset: If True, delete all existing records first.

    Returns:
        Number of documents inserted.
    """
    cursor = conn.cursor()

    if reset:
        logger.info("Resetting knowledge base table...")
        cursor.execute("DELETE FROM knowledge_base")
        conn.commit()
        logger.info("Table cleared")

    insert_sql = """
        INSERT INTO knowledge_base (title, content, category, embedding)
        VALUES (%s, %s, %s, %s)
    """

    inserted = 0
    for title, content, category, embedding in documents:
        cursor.execute(insert_sql, (title, content, category, embedding))
        inserted += 1

    conn.commit()
    cursor.close()

    return inserted


def verify_insertion(conn: psycopg2.extensions.connection) -> None:
    """Verify documents were inserted and test semantic search."""
    cursor = conn.cursor()

    # Count documents
    cursor.execute("SELECT COUNT(*) FROM knowledge_base")
    total = cursor.fetchone()[0]
    logger.info("Total documents in knowledge base: %d", total)

    # Count by category
    cursor.execute("SELECT category, COUNT(*) FROM knowledge_base GROUP BY category ORDER BY category")
    for category, count in cursor.fetchall():
        logger.info("  %s: %d documents", category, count)

    # Test semantic search
    logger.info("Testing semantic search with query: 'Will it rain?'")
    model = load_model()
    query_embedding = model.encode("Will it rain?").tolist()

    cursor.execute(
        """
        SELECT title, category, embedding <=> %s::vector AS distance
        FROM knowledge_base
        ORDER BY distance ASC
        LIMIT 3
        """,
        (query_embedding,),
    )

    logger.info("Top 3 results for 'Will it rain?':")
    for title, category, distance in cursor.fetchall():
        logger.info("  [%s] %s (distance: %.4f)", category, title, distance)

    cursor.close()


def main() -> None:
    """Main entry point for knowledge base ingestion."""
    parser = argparse.ArgumentParser(description="Ingest meteorological documents into pgvector knowledge base")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing records before inserting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show documents and embeddings without inserting",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Knowledge Base Ingestion Script")
    logger.info("=" * 60)
    logger.info("Documents to ingest: %d", len(DOCUMENTS))
    logger.info("Embedding model: %s (%d dims)", EMBEDDING_MODEL, EMBEDDING_DIM)

    if args.dry_run:
        logger.info("DRY RUN mode - no database operations will be performed")
        logger.info("-" * 60)
        for i, doc in enumerate(DOCUMENTS, 1):
            logger.info("[%d/%d] [%s] %s", i, len(DOCUMENTS), doc.category, doc.title)
            logger.info("     %s...", doc.content[:100])
        logger.info("-" * 60)
        logger.info("Dry run complete. %d documents would be ingested.", len(DOCUMENTS))
        return

    model = load_model()
    documents_with_embeddings = generate_embeddings(model, DOCUMENTS)

    db_url = get_db_url()
    logger.info("Database URL: %s", db_url.replace("weather:weather", "****:****"))

    conn = connect_to_db(db_url)

    try:
        inserted = insert_documents(conn, documents_with_embeddings, reset=args.reset)
        logger.info("Successfully inserted %d documents", inserted)

        verify_insertion(conn)

        logger.info("=" * 60)
        logger.info("Ingestion complete!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
