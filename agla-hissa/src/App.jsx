import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Signup from './routes/signUp';
import Login from './routes/Login';
import ChatPage from './routes/chatPage';


function App() {

  const sampleUserData = {
  "_id": {
    "$oid": "686f6c260bc7a32cacf04235"
  },
  "name": "Parth Katiyar",
  "email": "a@b.com",
  "password": "$2b$12$L5Z8uhr/eQN.EaDHdEEGVOD8DNf63fJB8HKH9/4aAB.IILxecRliW",
  "userId": "parth_katiyar_7b7f5a",
  "is_active": true,
  "threads": {
    "8ee807b9-ce2f-4c7b-99ec-709f78fd7ce9": {
      "thread_name": "cities",
      "documents": [
        {
          "docId": "cfcb1c5f-f327-4dee-a06a-a8cc92372736",
          "title": "Uttar_Pradesh.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Uttar_Pradesh_20250710130614.pdf"
        },
        {
          "docId": "080fa50b-c635-4782-97dc-e98d0667a54a",
          "title": "Lucknow.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Lucknow_20250710130614.pdf"
        },
        {
          "docId": "bc75fe06-9a4f-47c4-8b66-b0e5ae4b7292",
          "title": "Bombay_State.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Bombay_State_20250710130614.pdf"
        },
        {
          "docId": "01ea3aae-c015-4d41-b7b1-9541b1efbc12",
          "title": "Mumbai.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Mumbai_20250710130614.pdf"
        },
        {
          "docId": "16f8d734-2ca8-4a9e-839b-ceee17064473",
          "title": "Chennai.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Chennai_20250710130614.pdf"
        },
        {
          "docId": "803eb19d-6572-4143-9c5c-3ef64945f547",
          "title": "Delhi.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Delhi_20250710130614.pdf"
        },
        {
          "docId": "28f34d96-80c2-4326-bf13-42f3e1d75004",
          "title": "Kanpur.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:36:14.002Z"
          },
          "file_name": "Kanpur_20250710130614.pdf"
        }
      ],
      "chats": [
        {
          "type": "user",
          "content": "tell me about kanpur",
          "timestamp": {
            "$date": "2025-07-10T07:43:08.509Z"
          }
        },
        {
          "type": "agent",
          "content": "Kanpur is located in the central-western part of Uttar Pradesh, India, situated on the right bank of the Ganga. It was founded in 1207 by Raja Kanh Deo. Kanpur is known for its colonial architecture, gardens, sweets, dialect, and high-quality leather, plastic and textile products. It is also home to historical monuments such as the Jajmau Ghat, Kanpur Museum, Bhitargaon Temple, European Cemetery and Nanarao Park. Kanpur is an important economic center in India.",
          "timestamp": {
            "$date": "2025-07-10T07:43:08.509Z"
          }
        },
        {
          "type": "user",
          "content": "where is it located",
          "timestamp": {
            "$date": "2025-07-10T07:47:03.471Z"
          }
        },
        {
          "type": "agent",
          "content": "Kanpur is located in the central-western part of the state of Uttar Pradesh, India. It is situated on the right bank of the Ganga at 26.449923°N 80.331874°E. The city lies approximately 484 km from New Delhi and approximately 80 km from Lucknow and is part of the historical region of Awadh.",
          "timestamp": {
            "$date": "2025-07-10T07:47:03.471Z"
          }
        },
        {
          "type": "user",
          "content": "tell me some interesting facts",
          "timestamp": {
            "$date": "2025-07-10T07:52:24.805Z"
          }
        },
        {
          "type": "agent",
          "content": "Kanpur is located in the central-western part of Uttar Pradesh, India, and sits on the right bank of the Ganga. It is approximately 484 km from New Delhi and approximately 80 km from Lucknow. It is a part of the historical region of Awadh.",
          "timestamp": {
            "$date": "2025-07-10T07:52:24.805Z"
          }
        },
        {
          "type": "user",
          "content": "what about delhi",
          "timestamp": {
            "$date": "2025-07-10T07:54:50.360Z"
          }
        },
        {
          "type": "agent",
          "content": "I'm sorry, I don't have enough information to fulfill that request. You could try again, asking in a different way or adding more detail.",
          "timestamp": {
            "$date": "2025-07-10T07:54:50.360Z"
          }
        },
        {
          "type": "user",
          "content": "come on tell me something about delhi",
          "timestamp": {
            "$date": "2025-07-10T07:58:05.773Z"
          }
        },
        {
          "type": "agent",
          "content": "I'm sorry, I don't have enough information to provide you with interesting facts about Delhi.",
          "timestamp": {
            "$date": "2025-07-10T07:58:05.773Z"
          }
        },
        {
          "type": "user",
          "content": "anything at all",
          "timestamp": {
            "$date": "2025-07-10T07:58:24.893Z"
          }
        },
        {
          "type": "agent",
          "content": "Delhi is the capital of India, straddling the Yamuna river. It shares borders with Uttar Pradesh in the east and Haryana in the remaining directions. Delhi became a union territory on November 1, 1956, and the National Capital Territory (NCT) in 1995. The NCT covers an area of 1,484 square kilometres.",
          "timestamp": {
            "$date": "2025-07-10T07:58:24.893Z"
          }
        }
      ],
      "createdAt": {
        "$date": "2025-07-10T07:36:14.002Z"
      },
      "updatedAt": {
        "$date": "2025-07-10T07:58:24.893Z"
      }
    },
    "c01baa07-5a1f-4005-83f2-157ea375e021": {
      "thread_name": "cities2",
      "documents": [
        {
          "docId": "f5ef9b1c-7005-4b75-8aba-feb119e407b4",
          "title": "Uttar_Pradesh.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Uttar_Pradesh_20250710132902.pdf"
        },
        {
          "docId": "c399f7f5-2fb1-45ed-bea4-41a0196d0d07",
          "title": "Lucknow.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Lucknow_20250710132902.pdf"
        },
        {
          "docId": "a07328d3-b05d-4f5c-93dc-acbf32b93836",
          "title": "Bombay_State.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Bombay_State_20250710132902.pdf"
        },
        {
          "docId": "bc097df0-2091-497e-aca4-f391c6bb1a66",
          "title": "Mumbai.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Mumbai_20250710132902.pdf"
        },
        {
          "docId": "383a9911-131d-4a12-a455-6f7d923a70a6",
          "title": "Chennai.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Chennai_20250710132902.pdf"
        },
        {
          "docId": "f5f912c8-4125-4e56-b64a-1dc4b4d9909a",
          "title": "Delhi.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Delhi_20250710132902.pdf"
        },
        {
          "docId": "5f5c4b89-09d9-497f-b32f-4a20352d4f17",
          "title": "Kanpur.pdf",
          "type": "pdf",
          "time_uploaded": {
            "$date": "2025-07-10T07:59:02.141Z"
          },
          "file_name": "Kanpur_20250710132902.pdf"
        }
      ],
      "chats": [
        {
          "type": "user",
          "content": "tell me about kanpur",
          "timestamp": {
            "$date": "2025-07-10T08:11:59.869Z"
          }
        },
        {
          "type": "agent",
          "content": "Kanpur is a commercial center of northern India that was founded in 1207 by Raja Kanh Deo. It is situated on the right bank of the Ganga River in the central-western part of Uttar Pradesh. The city is approximately 484 km from New Delhi and 80 km from Lucknow. Kanpur is the 12th most populous city in India. It is also known for its colonial architecture, gardens, sweets, dialect, and high-quality leather, plastic and textile products.  Kanpur is an important economic center in India with a GDP of ~$9Bn.",
          "timestamp": {
            "$date": "2025-07-10T08:11:59.869Z"
          }
        },
        {
          "type": "user",
          "content": "full name of nelson mandela",
          "timestamp": {
            "$date": "2025-07-10T08:12:39.823Z"
          }
        },
        {
          "type": "agent",
          "content": "Nelson Mandela's full name is Nelson Rolihlahla Mandela.",
          "timestamp": {
            "$date": "2025-07-10T08:12:39.823Z"
          }
        },
        {
          "type": "user",
          "content": "tell me some interesting facts about delhi",
          "timestamp": {
            "$date": "2025-07-10T08:16:48.037Z"
          }
        },
        {
          "type": "agent",
          "content": "Here are some facts about Delhi:\n\n*   Official website (http://delhi.gov.in)\n*   Delhi (http://ucblibraries.summon.serialssolutions.com/#!/search?ho=t&l=en&q=Delhi) web resources provided by GovPubs at the University of Colorado Boulder Libraries\n*   Delhi (https://www.britannica.com/EBchecked/topic/156501) at the Encyclopædia Britannica\n*   Wikimedia Atlas of Delhi\n*   Geographic data related to Delhi (https://www.openstreetmap.org/relation/1942586) at OpenStreetMap",
          "timestamp": {
            "$date": "2025-07-10T08:16:48.037Z"
          }
        },
        {
          "type": "user",
          "content": "now chennai",
          "timestamp": {
            "$date": "2025-07-10T08:19:47.731Z"
          }
        },
        {
          "type": "agent",
          "content": "Here are some facts about Chennai:\n\n*   Chennai is the sixth-most-populous city in India per the 2011 Indian census.\n*   It forms the fourth-most-populous urban agglomeration.\n*   The Greater Chennai Corporation, incorporated in 1688, is the oldest municipal corporation in India and the second oldest in the world, after London.\n*   Historically, the region was part of the Chola, Pandya, Pallava, and Vijayanagara kingdoms during various eras.\n*   In 2011, the city had a population of 4,646,732 within an area of 174 km2 (67 sq mi).\n*   After the city expanded to 426 km2 (164 sq mi), the Chennai Municipal Corporation was renamed Greater Chennai Corporation, and the population, including the new city limits as per the 2011 census, was 6,748,026.\n*   Chennai is located on the southeastern coast of India in the northeastern part of Tamil Nadu on a flat coastal plain known as the Eastern Coastal Plains.\n*   The average elevation is 6.7 m (22 ft), and the highest point is at 60 m (200 ft).\n*   Chennai's soil is mostly clay, shale, and sandstone.\n*   A resident of Chennai is called a Chennaite.\n*   Chennai has six sister cities.",
          "timestamp": {
            "$date": "2025-07-10T08:19:47.731Z"
          }
        }
      ],
      "createdAt": {
        "$date": "2025-07-10T07:59:02.141Z"
      },
      "updatedAt": {
        "$date": "2025-07-10T08:19:47.731Z"
      }
    },
    "88b261e2-409b-40df-8475-a2ef02c185b2": {
      "thread_name": "cities2",
      "documents": [
        {
          "docId": "a0ef1073-4fa5-4b53-8f17-6b13ab6df0b7",
          "title": "Screenshot 2025-06-25 195502.png",
          "type": "png",
          "time_uploaded": {
            "$date": "2025-07-10T08:44:32.461Z"
          },
          "file_name": "Screenshot 2025-06-25 195502_20250710141432.png"
        }
      ],
      "chats": [],
      "createdAt": {
        "$date": "2025-07-10T08:44:32.461Z"
      },
      "updatedAt": {
        "$date": "2025-07-10T08:44:32.461Z"
      }
    }
  }
}
  const isLoggedIn = true;
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/chat"
          element={isLoggedIn ? <ChatPage userData={sampleUserData} /> : <Navigate to="/login" />}
        />
        <Route path="*" element={<Navigate to={isLoggedIn ? "/chat" : "/login"} />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
