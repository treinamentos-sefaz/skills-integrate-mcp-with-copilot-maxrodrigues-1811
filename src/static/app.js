document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySearch = document.getElementById("activity-search");
  const categoryFilter = document.getElementById("category-filter");
  const activitySort = document.getElementById("activity-sort");
  const activitiesCount = document.getElementById("activities-count");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const userMenuButton = document.getElementById("user-menu-button");
  const userMenu = document.getElementById("user-menu");
  const teacherStatus = document.getElementById("teacher-status");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  const cancelLoginButton = document.getElementById("cancel-login");
  let teacherUsername = null;
  let allActivities = {};

  activitySearch.addEventListener("input", renderActivities);
  categoryFilter.addEventListener("change", renderActivities);
  activitySort.addEventListener("change", renderActivities);

  function updateAuthUI() {
    const isTeacher = Boolean(teacherUsername);
    signupContainer.classList.toggle("hidden", !isTeacher);
    loginButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    teacherStatus.classList.toggle("hidden", !isTeacher);
    teacherStatus.textContent = isTeacher ? `Signed in: ${teacherUsername}` : "";
  }

  userMenuButton.addEventListener("click", () => {
    const isExpanded = userMenuButton.getAttribute("aria-expanded") === "true";
    userMenuButton.setAttribute("aria-expanded", String(!isExpanded));
    userMenu.classList.toggle("hidden", isExpanded);
  });

  loginButton.addEventListener("click", () => {
    userMenu.classList.add("hidden");
    userMenuButton.setAttribute("aria-expanded", "false");
    loginMessage.className = "hidden";
    loginMessage.textContent = "";
    loginDialog.showModal();
  });

  cancelLoginButton.addEventListener("click", () => loginDialog.close());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginMessage.className = "hidden";

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign in.");
      }

      teacherUsername = result.username;
      updateAuthUI();
      loginDialog.close();
      loginForm.reset();
      await fetchActivities();
    } catch (error) {
      loginMessage.textContent = error.message || "Unable to sign in.";
      loginMessage.className = "message error";
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to sign out. Please try again.");
      }

      teacherUsername = null;
      updateAuthUI();
      userMenu.classList.add("hidden");
      userMenuButton.setAttribute("aria-expanded", "false");
      await fetchActivities();
    } catch (error) {
      messageDiv.textContent = error.message || "Unable to sign out.";
      messageDiv.className = "message error";
    }
  });

  async function checkSession() {
    try {
      const response = await fetch("/auth/me");
      if (!response.ok) {
        throw new Error("Unable to check teacher login.");
      }
      const result = await response.json();
      teacherUsername = result.authenticated ? result.username : null;
    } catch (error) {
      console.error("Error checking teacher login:", error);
      teacherUsername = null;
    }
    updateAuthUI();
    await fetchActivities();
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      allActivities = await response.json();

      while (activitySelect.options.length > 1) {
        activitySelect.remove(1);
      }

      const selectedCategory = categoryFilter.value;
      const categories = [
        ...new Set(Object.values(allActivities).map((activity) => activity.category)),
      ].sort((left, right) => left.localeCompare(right));
      categoryFilter.replaceChildren(new Option("All categories", ""));
      categories.forEach((category) => {
        categoryFilter.add(new Option(category, category));
      });
      if (categories.includes(selectedCategory)) {
        categoryFilter.value = selectedCategory;
      }

      Object.keys(allActivities)
        .sort((left, right) => left.localeCompare(right))
        .forEach((name) => {
          const option = document.createElement("option");
          option.value = name;
          option.textContent = name;
          activitySelect.appendChild(option);
        });

      renderActivities();
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  function normalizeSearchText(value) {
    return value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase();
  }

  function renderActivities() {
    const query = normalizeSearchText(activitySearch.value.trim());
    const selectedCategory = categoryFilter.value;
    const sortOrder = activitySort.value;
    const matchingActivities = Object.entries(allActivities).filter(
      ([name, details]) => {
        if (selectedCategory && details.category !== selectedCategory) {
          return false;
        }

        const searchableText = normalizeSearchText(
          [name, details.category, details.description, details.schedule].join(" ")
        );
        return searchableText.includes(query);
      }
    );

    matchingActivities.sort(([leftName, left], [rightName, right]) => {
      if (sortOrder === "name" || sortOrder === "name-desc") {
        const nameOrder = leftName.localeCompare(rightName);
        return sortOrder === "name-desc" ? -nameOrder : nameOrder;
      }

      const scheduleOrder =
        (left.schedule_sort_order ?? Number.MAX_SAFE_INTEGER) -
        (right.schedule_sort_order ?? Number.MAX_SAFE_INTEGER);
      const order =
        scheduleOrder || leftName.localeCompare(rightName);
      return sortOrder === "schedule-desc" ? -order : order;
    });

    activitiesList.replaceChildren();
    activitiesCount.textContent = `Showing ${matchingActivities.length} of ${
      Object.keys(allActivities).length
    } activities`;

    if (matchingActivities.length === 0) {
      const emptyMessage = document.createElement("p");
      emptyMessage.className = "activity-empty";
      emptyMessage.textContent = "No activities match your search and filters.";
      activitiesList.appendChild(emptyMessage);
      return;
    }

    matchingActivities.forEach(([name, details]) => {
      const activityCard = document.createElement("div");
      activityCard.className = "activity-card";

      const spotsLeft =
        details.max_participants - details.participants.length;

      // Create participants HTML with delete icons instead of bullet points
      const participantsHTML =
        details.participants.length > 0
          ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => `<li>
                      <span class="participant-email">${email}</span>
                      ${
                        teacherUsername
                          ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Remove ${email} from ${name}">❌</button>`
                          : ""
                      }
                    </li>`
                  )
                  .join("")}
              </ul>
            </div>`
          : `<p><em>No participants yet</em></p>`;

      activityCard.innerHTML = `
          <h4>${name}</h4>
          <p><strong>Category:</strong> ${details.category}</p>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

      activitiesList.appendChild(activityCard);
    });

    activitiesList.querySelectorAll(".delete-btn").forEach((button) => {
      button.addEventListener("click", handleUnregister);
    });
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize authentication before rendering teacher-only controls.
  checkSession();
});
