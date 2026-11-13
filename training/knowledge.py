# Company knowledge the AI retrieves at question time (the "R" in RAG).
# This file is a BA-owned asset: edit definitions and examples here, then re-run train.py.
# All SQL uses the SQLite dialect.

DOCUMENTATION = [
    "The dataset covers orders from 2003-01 to 2005-05. There is no data for the current year, "
    "so 'last month' or 'this year' questions should use the latest dates present in the data.",
    "Dates are stored as text in YYYY-MM-DD format. Use strftime('%Y', col) for the year and "
    "strftime('%Y-%m', col) for the month.",
    "Revenue (doanh thu) = SUM(orderdetails.quantityOrdered * orderdetails.priceEach), "
    "counting orders whose status is not 'Cancelled'.",
    "Gross profit (lợi nhuận gộp) = SUM(quantityOrdered * (priceEach - products.buyPrice)).",
    "Best-selling products (sản phẩm bán chạy) are ranked by SUM(orderdetails.quantityOrdered), "
    "unless the user explicitly asks for revenue.",
    "Cash collected (tiền đã thu) comes from payments.amount, not from orders.",
    "Order status values: Shipped, Resolved, Cancelled, On Hold, Disputed, In Process.",
    "products.quantityInStock is the current stock level. Slow-moving stock = products with high "
    "quantityInStock and low total quantityOrdered. Inventory turnover = units sold / quantityInStock.",
    "A sales rep (nhân viên bán hàng) is an employee with jobTitle 'Sales Rep'; "
    "customers.salesRepEmployeeNumber links a customer to a rep.",
    "Offices are linked to employees via employees.officeCode. Office performance = revenue of "
    "customers handled by reps in that office.",
]

_TOP_PRODUCTS = (
    "SELECT p.productName, SUM(od.quantityOrdered) AS total_quantity "
    "FROM orderdetails od JOIN products p ON p.productCode = od.productCode "
    "GROUP BY p.productCode, p.productName ORDER BY total_quantity DESC LIMIT 5"
)

QA_PAIRS = [
    ("Top 5 best-selling products by quantity?", _TOP_PRODUCTS),
    ("Top 5 sản phẩm bán chạy nhất?", _TOP_PRODUCTS),
    ("Doanh thu theo từng tháng năm 2004?",
     "SELECT strftime('%Y-%m', o.orderDate) AS month, SUM(od.quantityOrdered * od.priceEach) AS revenue "
     "FROM orders o JOIN orderdetails od ON od.orderNumber = o.orderNumber "
     "WHERE strftime('%Y', o.orderDate) = '2004' AND o.status <> 'Cancelled' GROUP BY month ORDER BY month"),
    ("Monthly revenue trend",
     "SELECT strftime('%Y-%m', o.orderDate) AS month, SUM(od.quantityOrdered * od.priceEach) AS revenue "
     "FROM orders o JOIN orderdetails od ON od.orderNumber = o.orderNumber "
     "WHERE o.status <> 'Cancelled' GROUP BY month ORDER BY month"),
    ("Khách hàng nào chi tiêu nhiều nhất?",
     "SELECT c.customerName, SUM(od.quantityOrdered * od.priceEach) AS total_spent "
     "FROM customers c JOIN orders o ON o.customerNumber = c.customerNumber "
     "JOIN orderdetails od ON od.orderNumber = o.orderNumber WHERE o.status <> 'Cancelled' "
     "GROUP BY c.customerNumber, c.customerName ORDER BY total_spent DESC LIMIT 10"),
    ("Số lượng đơn hàng theo trạng thái?",
     "SELECT status, COUNT(*) AS order_count FROM orders GROUP BY status ORDER BY order_count DESC"),
    ("Which products have the highest stock but sell the least (slow-moving)?",
     "SELECT p.productName, p.quantityInStock, COALESCE(SUM(od.quantityOrdered), 0) AS units_sold "
     "FROM products p LEFT JOIN orderdetails od ON od.productCode = p.productCode "
     "GROUP BY p.productCode, p.productName, p.quantityInStock "
     "ORDER BY p.quantityInStock DESC, units_sold ASC LIMIT 10"),
    ("Mặt hàng nào tồn kho nhiều nhất?",
     "SELECT productName, quantityInStock FROM products ORDER BY quantityInStock DESC LIMIT 10"),
    ("Nhân viên bán hàng giỏi nhất là ai?",
     "SELECT e.firstName || ' ' || e.lastName AS sales_rep, SUM(od.quantityOrdered * od.priceEach) AS revenue "
     "FROM employees e JOIN customers c ON c.salesRepEmployeeNumber = e.employeeNumber "
     "JOIN orders o ON o.customerNumber = c.customerNumber "
     "JOIN orderdetails od ON od.orderNumber = o.orderNumber WHERE o.status <> 'Cancelled' "
     "GROUP BY e.employeeNumber, sales_rep ORDER BY revenue DESC LIMIT 5"),
    ("Văn phòng nào có doanh số tốt nhất?",
     "SELECT f.city AS office, SUM(od.quantityOrdered * od.priceEach) AS revenue "
     "FROM offices f JOIN employees e ON e.officeCode = f.officeCode "
     "JOIN customers c ON c.salesRepEmployeeNumber = e.employeeNumber "
     "JOIN orders o ON o.customerNumber = c.customerNumber "
     "JOIN orderdetails od ON od.orderNumber = o.orderNumber WHERE o.status <> 'Cancelled' "
     "GROUP BY f.officeCode, f.city ORDER BY revenue DESC"),
    ("Revenue by product line",
     "SELECT p.productLine, SUM(od.quantityOrdered * od.priceEach) AS revenue "
     "FROM orderdetails od JOIN products p ON p.productCode = od.productCode "
     "JOIN orders o ON o.orderNumber = od.orderNumber WHERE o.status <> 'Cancelled' "
     "GROUP BY p.productLine ORDER BY revenue DESC"),
    ("Gross profit by product line",
     "SELECT p.productLine, SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) AS gross_profit "
     "FROM orderdetails od JOIN products p ON p.productCode = od.productCode "
     "JOIN orders o ON o.orderNumber = od.orderNumber WHERE o.status <> 'Cancelled' "
     "GROUP BY p.productLine ORDER BY gross_profit DESC"),
    ("Doanh thu theo quốc gia khách hàng?",
     "SELECT c.country, SUM(od.quantityOrdered * od.priceEach) AS revenue "
     "FROM customers c JOIN orders o ON o.customerNumber = c.customerNumber "
     "JOIN orderdetails od ON od.orderNumber = o.orderNumber WHERE o.status <> 'Cancelled' "
     "GROUP BY c.country ORDER BY revenue DESC LIMIT 10"),
    ("Total payments collected per year",
     "SELECT strftime('%Y', paymentDate) AS year, SUM(amount) AS collected "
     "FROM payments GROUP BY year ORDER BY year"),
    ("Khách hàng nào có đơn hàng bị hủy hoặc tranh chấp?",
     "SELECT c.customerName, o.status, COUNT(*) AS order_count "
     "FROM customers c JOIN orders o ON o.customerNumber = c.customerNumber "
     "WHERE o.status IN ('Cancelled', 'Disputed') GROUP BY c.customerNumber, c.customerName, o.status "
     "ORDER BY order_count DESC"),
    ("Average order value",
     "SELECT AVG(order_total) AS avg_order_value FROM ("
     "SELECT o.orderNumber, SUM(od.quantityOrdered * od.priceEach) AS order_total "
     "FROM orders o JOIN orderdetails od ON od.orderNumber = o.orderNumber "
     "WHERE o.status <> 'Cancelled' GROUP BY o.orderNumber) t"),
    ("Top 5 products by profit margin",
     "SELECT productName, ROUND((MSRP - buyPrice) / MSRP * 100, 1) AS margin_pct "
     "FROM products ORDER BY margin_pct DESC LIMIT 5"),
]
