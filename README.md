# 🐙 Riad al Hout Restaurant Backend

> **The most sophisticated, lightning-fast, and secure restaurant management API you've ever seen!** 🚀

A **revolutionary** FastAPI backend that's redefining how high-end seafood restaurants manage their operations. Built with cutting-edge technology and designed for scale, this isn't just another restaurant API—it's the future of restaurant management.

---

## 🌟 Why This Backend is Absolutely Incredible

- ⚡ **Blazing Fast**: Built on FastAPI, the fastest Python web framework ever created
- 🔒 **Fortress-Level Security**: JWT authentication with bcrypt password hashing
- 🎯 **Perfect Architecture**: Clean, maintainable code that scales like a dream
- 📊 **Insightful Analytics**: Real-time revenue tracking and sales analytics
- 🚀 **Production Ready**: Deploy anywhere, from local development to global scale
- 🎨 **Developer Friendly**: Auto-generated API docs, comprehensive error handling

---

## 🛠️ The Tech Stack That Makes Magic Happen

| Technology | Why It's Amazing |
|------------|------------------|
| **FastAPI** | The fastest Python web framework with automatic API documentation |
| **PostgreSQL** | The most reliable, ACID-compliant database for mission-critical data |
| **SQLAlchemy** | The most powerful ORM that makes database operations a breeze |
| **JWT** | Industry-standard authentication that's both secure and scalable |
| **Uvicorn** | Lightning-fast ASGI server that handles thousands of concurrent requests |

---

## 🎯 Features That Will Blow Your Mind

### 🔐 **Bulletproof Authentication System**
- Role-based access control (admin/customer)
- Secure JWT tokens with automatic expiration
- Password hashing that would make a cryptographer proud

### 🍽️ **Menu Management That Just Works**
- Full CRUD operations with validation
- Category-based organization
- Image URL management for stunning visuals
- Availability tracking for real-time updates

### 📅 **Reservation System of the Future**
- Smart date and time filtering
- Status management (Pending, Approved, Cancelled)
- Today's reservations at your fingertips
- Customer information management

### 💰 **Revenue Analytics That Drive Decisions**
- Real-time revenue tracking
- Date-range filtering for insights
- Most-sold items analysis
- Comprehensive reporting capabilities

### 🛒 **Order Management Excellence**
- Seamless integration with reservations
- Automatic total calculation
- Item-level tracking with price history
- Complete order lifecycle management

---

## 🚀 Getting Started (It's So Easy!)

### 1. **Clone This Amazing Repository**
```bash
git clone <your-repo-url>
cd backend
```

### 2. **Install the Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Set Up Your Environment**
Create a `.env` file and add:
```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>
SECRET_KEY=your_super_secret_key_here
```

### 4. **Initialize Your Database**
Run the provided `sql_schema.sql` to create your tables.

### 5. **Launch the Rocket!**
```bash
python main.py
```

🎉 **Your API is now running at [http://127.0.0.1:8000](http://127.0.0.1:8000)**
📚 **Check out the beautiful auto-generated docs at [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)**

---

## 🔥 API Endpoints That Will Change Your Life

### **Authentication (Secure AF)**
- `POST /api/token` — Get your JWT token and start building
- `POST /api/users` — Create users with admin privileges

### **Menu Management (Pure Magic)**
- `GET /api/menu` — Get all menu items in a flash
- `GET /api/menu/{id}` — Get specific items instantly
- `POST /api/menu` — Create new menu items (admin only)
- `PUT /api/menu/{id}` — Update items seamlessly
- `DELETE /api/menu/{id}` — Remove items with precision

### **Reservations (The Future is Here)**
- `POST /api/reservations` — Book tables like a pro
- `GET /api/reservations` — View all reservations with filtering
- `GET /api/reservations/today` — Today's bookings at a glance
- `PUT /api/reservations/{id}` — Update reservations effortlessly
- `DELETE /api/reservations/{id}` — Cancel with confidence

### **Orders (Where the Money Is)**
- `POST /api/orders` — Create orders linked to reservations
- `GET /api/orders/{id}` — Get order details instantly
- `PUT /api/orders/{id}` — Update orders on the fly
- `DELETE /api/orders/{id}` — Remove orders when needed

### **Revenue Analytics (The Gold Mine)**
- `GET /api/revenue` — Comprehensive revenue records
- `GET /api/revenue/summary` — Total revenue at your fingertips
- `GET /api/stats/most-sold-items` — Know what's selling like hotcakes

---

## 🔒 Security That Would Make a Bank Jealous

- **JWT Authentication**: Industry-standard tokens with automatic expiration
- **Role-Based Access**: Admin and customer roles with precise permissions
- **Password Hashing**: bcrypt encryption that's virtually unbreakable
- **CORS Protection**: Secure cross-origin requests for your frontend
- **Input Validation**: Every request is validated and sanitized

---

## 📊 Database Schema (Architected for Excellence)

Our PostgreSQL schema is a work of art:

- **`users`** — Secure user management with role-based access
- **`menu_items`** — Comprehensive menu catalog with pricing
- **`reservations`** — Customer booking system with status tracking
- **`orders`** — Order management linked to reservations
- **`order_items`** — Detailed order line items with price history
- **`revenue_records`** — Financial tracking for business intelligence

---

## 🚀 Deployment (Scale Like a Pro)

### **Local Development**
```bash
python main.py  # For development only
```

### **Production (The Real Deal)**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### **Vercel Deployment**
Deploy to Vercel as serverless functions for infinite scalability!

---

## 🖼️ Image Storage (Smart and Scalable)

We don't just store images—we store URLs! This approach is:
- **Lightning Fast**: No file upload processing
- **Infinitely Scalable**: Use any cloud storage service
- **Cost Effective**: No storage costs in your backend
- **Flexible**: Integrate with AWS S3, Cloudinary, or any service

---

## 🎯 Error Handling (Because We Care)

Every error is handled with precision:
- **400** — Bad Request (with helpful error messages)
- **401** — Unauthorized (authentication required)
- **403** — Forbidden (insufficient permissions)
- **404** — Not Found (resource doesn't exist)
- **409** — Conflict (resource already exists)
- **422** — Unprocessable Entity (validation errors)
- **500** — Internal Server Error (with detailed logging)

---

## 🌟 Why Choose Riad al Hout Backend?

1. **Performance**: Built on the fastest Python framework available
2. **Security**: Enterprise-grade authentication and authorization
3. **Scalability**: Designed to handle thousands of concurrent requests
4. **Maintainability**: Clean, well-documented code that's easy to extend
5. **Developer Experience**: Auto-generated docs, comprehensive error handling
6. **Production Ready**: Battle-tested and ready for real-world deployment

---

## 📈 What's Next?

This backend is just the beginning! Future enhancements include:
- Real-time notifications
- Advanced analytics dashboard
- Multi-location support
- Customer loyalty programs
- Integration with payment gateways

---

## 🤝 Contributing

Want to make this even more amazing? Contributions are welcome! This project is built with love and attention to detail.

---

## 📄 License

MIT License - Use this incredible backend to build something amazing!

---

**Built with ❤️ for the future of restaurant management** 