import http from 'node:http';

/**
 * A stand-in menu site for the self-test. It deliberately mirrors the two
 * shapes the real extractor has to cope with: meal data fetched as JSON from an
 * API, and the same meals rendered as cards in the DOM. It is NOT a model of
 * CookUnity's actual markup — it exists to prove the extraction machinery runs.
 */

const CHEFS = ['Maria Alvarez', 'Ken Tanaka', 'Amara Osei', 'Luca Rossi'];
const CUISINES = ['Indian', 'Japanese', 'West African', 'Italian'];
const NAMES = [
  'Chicken Tikka Masala',
  'Miso Glazed Salmon',
  'Jollof Rice Bowl',
  'Chicken Parmesan',
  'Pad Thai Noodles',
  'Beef Bulgogi',
  'Shrimp Scampi',
  'Harissa Cauliflower',
  'Turkey Meatballs',
  'Coconut Curry Tofu',
  'Steak Chimichurri',
  'Lemon Herb Chicken',
];

export const MEALS = NAMES.map((name, i) => ({
  id: `meal-${1000 + i}`,
  name,
  description: `${name} with seasonal vegetables and a house-made sauce.`,
  chef: { name: CHEFS[i % CHEFS.length] },
  price: { amount: 1199 + i * 50, currency: 'USD' },
  nutritionalInfo: {
    calories: 420 + i * 17,
    protein: 28 + i,
    carbs: 30 + i * 2,
    fat: 12 + i,
  },
  rating: Number((4.2 + (i % 8) * 0.1).toFixed(1)),
  reviewCount: 120 + i * 37,
  tags: ['high-protein', i % 2 === 0 ? 'gluten-free' : 'dairy-free'],
  category: CUISINES[i % CUISINES.length],
  imageUrl: `/img/${i}.jpg`,
}));

const card = (meal) => {
  const price = (meal.price.amount / 100).toFixed(2);
  const n = meal.nutritionalInfo;
  return `
    <div class="meal-card-7f3a9b">
      <a href="/meal/${meal.id}"><img src="${meal.imageUrl}" alt="${meal.name}"></a>
      <h3>${meal.name}</h3>
      <p class="chef">by ${meal.chef.name}</p>
      <div class="macros">${n.calories} cal &middot; ${n.protein}g protein &middot; ${n.carbs}g carbs &middot; ${n.fat}g fat</div>
      <div class="rating">${meal.rating} &#9733; (${meal.reviewCount} reviews)</div>
      <div class="price">$${price}</div>
    </div>`;
};

const menuPage = (meals, { withFetch }) => `<!doctype html>
<html><head><title>Fixture Menu</title></head>
<body>
  <h1>This Week's Menu</h1>
  <div class="grid">${meals.map(card).join('')}</div>
  ${withFetch ? '<script>fetch("/api/meals").then(r => r.json());</script>' : ''}
</body></html>`;

const embeddedPage = (meals) => `<!doctype html>
<html><head><title>Fixture Embedded</title></head>
<body>
  <h1>This Week's Menu</h1>
  <script id="__NEXT_DATA__" type="application/json">
    ${JSON.stringify({ props: { pageProps: { menu: { products: meals } } } })}
  </script>
</body></html>`;

export function startFixture(port = 0) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? '/', 'http://127.0.0.1');
    if (url.pathname === '/api/meals') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ data: { menu: { products: MEALS } } }));
      return;
    }
    if (url.pathname === '/embedded') {
      res.writeHead(200, { 'content-type': 'text/html' });
      res.end(embeddedPage(MEALS));
      return;
    }
    if (url.pathname === '/dom-only') {
      res.writeHead(200, { 'content-type': 'text/html' });
      res.end(menuPage(MEALS, { withFetch: false }));
      return;
    }
    if (url.pathname.startsWith('/img/')) {
      res.writeHead(200, { 'content-type': 'image/svg+xml' });
      res.end('<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>');
      return;
    }
    res.writeHead(200, { 'content-type': 'text/html' });
    res.end(menuPage(MEALS, { withFetch: true }));
  });

  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => {
      const address = server.address();
      const actualPort = typeof address === 'object' && address ? address.port : port;
      resolve({
        baseUrl: `http://127.0.0.1:${actualPort}`,
        close: () => new Promise((done) => server.close(() => done(undefined))),
      });
    });
  });
}
