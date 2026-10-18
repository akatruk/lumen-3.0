import { Composition, registerRoot } from "remotion";
import { PriceChange, PriceCounter, PropertyComparison, PurchaseProcess, RentalYield } from "./scenes";

const size = { fps: 30, width: 1080, height: 1920, durationInFrames: 90 };

export function RealEstateRoot() {
  return (
    <>
      <Composition id="RePriceCounter" {...size} component={PriceCounter} defaultProps={{ locale: "en-US", currency: "USD", value: 240000 }} />
      <Composition id="RePriceChange" {...size} component={PriceChange} defaultProps={{ locale: "en-US", currency: "USD", previous: 240000, next: 228000 }} />
      <Composition id="ReRentalYield" {...size} component={RentalYield} defaultProps={{ locale: "en-US", currency: "USD", monthlyRent: 1800, yieldPercent: 5.4 }} />
      <Composition id="RePropertyComparison" {...size} component={PropertyComparison} defaultProps={{ locale: "en-US", left: { name: "Riverside", priceLabel: "Lower fees" }, right: { name: "Central", priceLabel: "Shorter commute" } }} />
      <Composition id="RePurchaseProcess" {...size} component={PurchaseProcess} defaultProps={{ locale: "en-US" }} />
    </>
  );
}

registerRoot(RealEstateRoot);
