"""
Machine Learning model for Data Center Location Recommendation
Uses existing infrastructure data to predict optimal future locations
"""

import asyncio
import json
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

# Import from the main application
from main import calculate_proximity_scores_batch, INFRASTRUCTURE_CACHE


class DataCenterLocationML:
    """ML model to recommend data center locations based on infrastructure proximity"""

    def __init__(self):
        self.existing_locations_df = None
        self.feature_importance = {}
        self.trained = False

    async def load_existing_datacenters(self, csv_path: str = "existing_datacenters.csv") -> pd.DataFrame:
        """Load existing data center locations from CSV"""
        print(f"📂 Loading existing data center locations from {csv_path}...")
        df = pd.read_csv(csv_path)

        # Remove duplicates based on coordinates
        df_unique = df.drop_duplicates(subset=['Latitude', 'Longitude'])
        print(f"✅ Loaded {len(df)} locations ({len(df_unique)} unique coordinates)")

        self.existing_locations_df = df_unique
        return df_unique

    async def extract_infrastructure_features(self, locations_df: pd.DataFrame) -> pd.DataFrame:
        """Extract infrastructure features for given locations using existing scoring system"""
        print(f"🔍 Extracting infrastructure features for {len(locations_df)} locations...")

        # Prepare sites for infrastructure analysis
        sites = []
        for _, row in locations_df.iterrows():
            sites.append({
                "site_name": row.get("Data Centre Name", "Unknown"),
                "technology_type": "datacenter",  # Not renewable, but we use the same scoring
                "capacity_mw": 50.0,  # Average data center size assumption
                "latitude": row["Latitude"],
                "longitude": row["Longitude"],
                "commissioning_year": 2025,
                "is_btm": False,
                "development_status_short": "operational",
                "capacity_factor": 1.0,
            })

        # Use existing infrastructure scoring system
        proximity_scores = await calculate_proximity_scores_batch(sites)

        # Convert to DataFrame
        features = []
        for i, prox_score in enumerate(proximity_scores):
            feature_row = {
                "location_id": i,
                "latitude": sites[i]["latitude"],
                "longitude": sites[i]["longitude"],
                "site_name": sites[i]["site_name"],
                "substation_score": prox_score.get("substation_score", 0.0),
                "transmission_score": prox_score.get("transmission_score", 0.0),
                "fiber_score": prox_score.get("fiber_score", 0.0),
                "ixp_score": prox_score.get("ixp_score", 0.0),
                "water_score": prox_score.get("water_score", 0.0),
            }

            # Add distance features
            nearest_dist = prox_score.get("nearest_distances", {})
            feature_row.update({
                "substation_distance_km": nearest_dist.get("substation_km", 999.9),
                "transmission_distance_km": nearest_dist.get("transmission_km", 999.9),
                "fiber_distance_km": nearest_dist.get("fiber_km", 999.9),
                "ixp_distance_km": nearest_dist.get("ixp_km", 999.9),
                "water_distance_km": nearest_dist.get("water_km", 999.9),
            })

            features.append(feature_row)

        features_df = pd.DataFrame(features)
        print(f"✅ Extracted {len(features_df.columns)} features for each location")
        return features_df

    async def train_model(self) -> Dict[str, Any]:
        """
        Train ML model on existing data centers
        Since all existing locations are 'good', we use unsupervised learning to find patterns
        """
        print("🤖 Training ML model on existing data center locations...")

        if self.existing_locations_df is None:
            raise ValueError("Must load existing data centers first")

        # Extract features for existing locations
        features_df = await self.extract_infrastructure_features(self.existing_locations_df)

        # Calculate composite infrastructure score for each location
        feature_cols = [
            "substation_score", "transmission_score", "fiber_score",
            "ixp_score", "water_score"
        ]

        # Calculate statistics of existing "good" locations
        self.feature_stats = {
            "mean": features_df[feature_cols].mean().to_dict(),
            "std": features_df[feature_cols].std().to_dict(),
            "min": features_df[feature_cols].min().to_dict(),
            "max": features_df[feature_cols].max().to_dict(),
            "median": features_df[feature_cols].median().to_dict(),
        }

        # Calculate composite score - higher is better
        features_df["composite_score"] = (
            features_df["substation_score"] * 0.3 +
            features_df["transmission_score"] * 0.25 +
            features_df["fiber_score"] * 0.25 +
            features_df["ixp_score"] * 0.15 +
            features_df["water_score"] * 0.05
        )

        self.threshold_score = features_df["composite_score"].quantile(0.25)  # 25th percentile

        print(f"\n📊 Existing Data Center Infrastructure Profile:")
        print(f"   Average substation score: {self.feature_stats['mean']['substation_score']:.2f}")
        print(f"   Average transmission score: {self.feature_stats['mean']['transmission_score']:.2f}")
        print(f"   Average fiber score: {self.feature_stats['mean']['fiber_score']:.2f}")
        print(f"   Average IXP score: {self.feature_stats['mean']['ixp_score']:.2f}")
        print(f"   Average water score: {self.feature_stats['mean']['water_score']:.2f}")
        print(f"   Minimum acceptable composite score: {self.threshold_score:.2f}")

        self.trained = True
        self.training_data = features_df

        return {
            "model_type": "infrastructure_proximity_based",
            "training_samples": len(features_df),
            "feature_statistics": self.feature_stats,
            "threshold_score": self.threshold_score,
        }

    async def generate_candidate_locations(self, grid_spacing_deg: float = 0.25) -> List[Dict[str, float]]:
        """
        Generate candidate locations across UK using grid sampling
        grid_spacing_deg: spacing between candidate points in degrees (0.25 ≈ 28km)
        """
        print(f"🗺️  Generating candidate locations across UK (grid spacing: {grid_spacing_deg}°)...")

        # UK bounding box
        lat_min, lat_max = 50.0, 59.0
        lon_min, lon_max = -8.0, 2.0

        candidates = []
        lat = lat_min
        while lat <= lat_max:
            lon = lon_min
            while lon <= lon_max:
                candidates.append({
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "site_name": f"Candidate_{len(candidates)}",
                })
                lon += grid_spacing_deg
            lat += grid_spacing_deg

        print(f"✅ Generated {len(candidates)} candidate locations")
        return candidates

    async def score_candidate_location(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Score a single candidate location"""
        candidate_df = pd.DataFrame([{
            "Latitude": latitude,
            "Longitude": longitude,
            "Data Centre Name": "Candidate",
        }])

        features_df = await self.extract_infrastructure_features(candidate_df)

        # Calculate composite score
        composite_score = (
            features_df["substation_score"].iloc[0] * 0.3 +
            features_df["transmission_score"].iloc[0] * 0.25 +
            features_df["fiber_score"].iloc[0] * 0.25 +
            features_df["ixp_score"].iloc[0] * 0.15 +
            features_df["water_score"].iloc[0] * 0.05
        )

        # Determine if it meets threshold
        recommendation = "Recommended" if composite_score >= self.threshold_score else "Not Recommended"

        return {
            "latitude": latitude,
            "longitude": longitude,
            "composite_score": round(composite_score, 2),
            "recommendation": recommendation,
            "feature_scores": {
                "substation": round(features_df["substation_score"].iloc[0], 2),
                "transmission": round(features_df["transmission_score"].iloc[0], 2),
                "fiber": round(features_df["fiber_score"].iloc[0], 2),
                "ixp": round(features_df["ixp_score"].iloc[0], 2),
                "water": round(features_df["water_score"].iloc[0], 2),
            },
            "distances_km": {
                "substation": features_df["substation_distance_km"].iloc[0],
                "transmission": features_df["transmission_distance_km"].iloc[0],
                "fiber": features_df["fiber_distance_km"].iloc[0],
                "ixp": features_df["ixp_distance_km"].iloc[0],
                "water": features_df["water_distance_km"].iloc[0],
            }
        }

    async def recommend_locations(
        self,
        num_candidates: int = 100,
        top_n: int = 10,
        grid_spacing: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Generate and score candidate locations, return top recommendations

        Args:
            num_candidates: Number of random candidates to generate (in addition to grid)
            top_n: Number of top recommendations to return
            grid_spacing: Grid spacing for systematic coverage (degrees)
        """
        if not self.trained:
            raise ValueError("Model must be trained first")

        print(f"\n🎯 Generating location recommendations...")

        # Generate systematic grid candidates
        grid_candidates = await self.generate_candidate_locations(grid_spacing)

        # Sample a subset to avoid overwhelming the system
        import random
        if len(grid_candidates) > num_candidates:
            sampled_candidates = random.sample(grid_candidates, num_candidates)
        else:
            sampled_candidates = grid_candidates

        # Score all candidates
        print(f"📊 Scoring {len(sampled_candidates)} candidate locations...")
        scored_candidates = []

        for i, candidate in enumerate(sampled_candidates):
            if i % 20 == 0:
                print(f"   Progress: {i}/{len(sampled_candidates)}...")

            score_result = await self.score_candidate_location(
                candidate["latitude"],
                candidate["longitude"]
            )
            scored_candidates.append(score_result)

        # Sort by composite score
        scored_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        # Return top N
        top_recommendations = scored_candidates[:top_n]

        print(f"\n✅ Top {top_n} Recommended Locations:")
        print("=" * 80)
        for i, rec in enumerate(top_recommendations, 1):
            print(f"\n{i}. Location: ({rec['latitude']:.4f}, {rec['longitude']:.4f})")
            print(f"   Composite Score: {rec['composite_score']:.2f} (threshold: {self.threshold_score:.2f})")
            print(f"   Infrastructure Scores:")
            for infra_type, score in rec['feature_scores'].items():
                print(f"      - {infra_type}: {score:.2f}")

        return top_recommendations

    def get_training_summary(self) -> Dict[str, Any]:
        """Get summary of training data and model"""
        if not self.trained:
            return {"status": "not_trained"}

        return {
            "status": "trained",
            "training_samples": len(self.training_data),
            "feature_statistics": self.feature_stats,
            "threshold_score": self.threshold_score,
            "model_type": "infrastructure_proximity_based",
            "description": "Model learns from existing data center infrastructure proximity patterns"
        }


async def main():
    """Main execution function"""
    print("=" * 80)
    print("🏢 DATA CENTER LOCATION ML - MVP")
    print("=" * 80)

    # Initialize model
    ml_model = DataCenterLocationML()

    # Load existing data centers
    await ml_model.load_existing_datacenters("existing_datacenters.csv")

    # Train model
    training_result = await ml_model.train_model()
    print(f"\n✅ Model trained successfully!")
    print(f"   Training samples: {training_result['training_samples']}")
    print(f"   Model type: {training_result['model_type']}")

    # Generate recommendations
    recommendations = await ml_model.recommend_locations(
        num_candidates=50,  # Start small for MVP
        top_n=10,
        grid_spacing=1.0    # 1 degree ≈ 111km spacing
    )

    # Save recommendations to file
    output_file = "recommended_datacenter_locations.json"
    with open(output_file, "w") as f:
        json.dump({
            "model_info": ml_model.get_training_summary(),
            "top_recommendations": recommendations,
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
